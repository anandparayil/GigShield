from __future__ import annotations

import hashlib
import json
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import get_connection

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="GigShield Phase 2")

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def notify(cursor, user_id: int, title: str, message: str, type_: str = "info") -> None:
    cursor.execute(
        "INSERT INTO notifications (user_id, title, message, type) VALUES (%s, %s, %s, %s)",
        (user_id, title, message, type_),
    )


def dict_cursor():
    conn = get_connection()
    return conn, conn.cursor(dictionary=True)


def get_user_or_404(cursor, user_id: int) -> dict[str, Any]:
    cursor.execute("SELECT id, full_name, phone, city, zone_name, preferred_hours FROM users WHERE id = %s AND role = 'user'", (user_id,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_active_policy(cursor, user_id: int) -> dict[str, Any] | None:
    cursor.execute(
        '''
        SELECT *
        FROM policies
        WHERE user_id = %s AND status = 'ACTIVE'
        ORDER BY created_at DESC
        LIMIT 1
        ''',
        (user_id,),
    )
    return cursor.fetchone()


def calculate_premium_components(user: dict[str, Any], platforms: list[dict[str, Any]], plan_name: str) -> dict[str, Any]:
    plans = {
        "Basic": {"base": 35, "max_payout": 400, "coverage_hours": 3},
        "Plus": {"base": 65, "max_payout": 650, "coverage_hours": 4},
        "Max": {"base": 120, "max_payout": 900, "coverage_hours": 6},
    }
    if plan_name not in plans:
        raise HTTPException(status_code=400, detail="Invalid plan")

    base = float(plans[plan_name]["base"])
    additions: list[dict[str, Any]] = []
    deductions: list[dict[str, Any]] = []
    final_premium = base

    risky_zones = {"koramangala", "andheri east", "floodzone", "coastal", "potheri"}
    if user["zone_name"].strip().lower() in risky_zones:
        delta = round(base * 0.12, 2)
        final_premium += delta
        additions.append({"label": "High-risk zone loading", "amount": delta})

    hours = (user.get("preferred_hours") or "").lower()
    if any(token in hours for token in ["7", "8", "9", "peak", "dinner", "night"]):
        delta = round(base * 0.08, 2)
        final_premium += delta
        additions.append({"label": "Peak-hour worker loading", "amount": delta})

    total_trips = sum(int(p["trips_completed"]) for p in platforms)
    if total_trips >= 500:
        delta = round(base * 0.10, 2)
        final_premium -= delta
        deductions.append({"label": "High experience discount", "amount": delta})

    if len(platforms) >= 2:
        delta = round(base * 0.07, 2)
        final_premium -= delta
        deductions.append({"label": "Multi-platform flexibility discount", "amount": delta})

    avg_earning = 0
    if platforms:
        avg_earning = round(sum(float(p["avg_hourly_earning"]) for p in platforms) / len(platforms), 2)
        if avg_earning < 70:
            delta = round(base * 0.03, 2)
            final_premium -= delta
            deductions.append({"label": "Safe-income stability bonus", "amount": delta})

    final_premium = round(max(final_premium, 15.0), 2)
    return {
        "base_premium": base,
        "final_premium": final_premium,
        "max_payout": plans[plan_name]["max_payout"],
        "coverage_hours": plans[plan_name]["coverage_hours"],
        "breakdown": {
            "base": base,
            "additions": additions,
            "deductions": deductions,
            "total_trips": total_trips,
            "average_hourly_earning": avg_earning,
        },
    }


class PlatformInput(BaseModel):
    platform: str
    worker_code: str
    trips_completed: int = 0
    avg_hourly_earning: float = 80.0


class RegisterInput(BaseModel):
    full_name: str
    phone: str = Field(min_length=10, max_length=15)
    password: str = Field(min_length=4, max_length=50)
    city: str
    zone_name: str
    preferred_hours: str = ""
    platforms: list[PlatformInput]


class LoginInput(BaseModel):
    phone: str
    password: str


class PolicyInput(BaseModel):
    user_id: int
    plan_name: str


class TriggerInput(BaseModel):
    trigger_type: str
    city: str
    zone_name: str
    severity: str = "HIGH"
    description: str = ""


class ProfileUpdateInput(BaseModel):
    full_name: str
    city: str
    zone_name: str
    preferred_hours: str = ""


class PlatformUpdateInput(BaseModel):
    platform: str
    worker_code: str
    trips_completed: int
    avg_hourly_earning: float


@app.get("/")
def serve_home():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/login")
def serve_login():
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/register")
def serve_register():
    return FileResponse(FRONTEND_DIR / "register.html")


@app.get("/dashboard")
def serve_dashboard():
    return FileResponse(FRONTEND_DIR / "dashboard.html")


@app.get("/admin-login")
def serve_admin_login():
    return FileResponse(FRONTEND_DIR / "admin-login.html")


@app.get("/admin")
def serve_admin_dashboard():
    return FileResponse(FRONTEND_DIR / "admin-dashboard.html")


@app.post("/api/auth/register")
def register_user(payload: RegisterInput):
    if not payload.platforms:
        raise HTTPException(status_code=400, detail="Add at least one linked platform")

    conn, cursor = dict_cursor()
    try:
        cursor.execute("SELECT id FROM users WHERE phone = %s", (payload.phone,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Mobile number already registered")

        cursor.execute(
            '''
            INSERT INTO users (full_name, phone, password_hash, role, city, zone_name, preferred_hours)
            VALUES (%s, %s, %s, 'user', %s, %s, %s)
            ''',
            (
                payload.full_name,
                payload.phone,
                hash_password(payload.password),
                payload.city,
                payload.zone_name,
                payload.preferred_hours,
            ),
        )
        user_id = cursor.lastrowid

        for platform in payload.platforms:
            cursor.execute(
                '''
                INSERT INTO linked_platforms (user_id, platform, worker_code, trips_completed, avg_hourly_earning)
                VALUES (%s, %s, %s, %s, %s)
                ''',
                (
                    user_id,
                    platform.platform,
                    platform.worker_code,
                    platform.trips_completed,
                    platform.avg_hourly_earning,
                ),
            )

        notify(cursor, user_id, "Welcome to GigShield", "Your account is live. Add a policy to activate protection.", "success")
        conn.commit()

        return {"message": "Registration successful", "user_id": user_id}
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()


@app.post("/api/auth/login")
def login(payload: LoginInput):
    conn, cursor = dict_cursor()
    try:
        cursor.execute(
            '''
            SELECT id, full_name, phone, role
            FROM users
            WHERE phone = %s AND password_hash = %s
            ''',
            (payload.phone, hash_password(payload.password)),
        )
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid mobile number or password")
        return {"message": "Login successful", "user": user}
    finally:
        cursor.close()
        conn.close()


@app.get("/api/users/{user_id}/dashboard")
def get_user_dashboard(user_id: int):
    conn, cursor = dict_cursor()
    try:
        user = get_user_or_404(cursor, user_id)

        cursor.execute(
            '''
            SELECT id, platform, worker_code, trips_completed, avg_hourly_earning, status
            FROM linked_platforms
            WHERE user_id = %s
            ORDER BY platform
            ''',
            (user_id,),
        )
        platforms = cursor.fetchall()

        policy = get_active_policy(cursor, user_id)

        cursor.execute(
            '''
            SELECT c.id, c.payout_amount, c.claim_status, c.created_at, t.trigger_type, t.city, t.zone_name
            FROM claims c
            JOIN triggers t ON c.trigger_id = t.id
            WHERE c.user_id = %s
            ORDER BY c.created_at DESC
            LIMIT 5
            ''',
            (user_id,),
        )
        recent_claims = cursor.fetchall()

        cursor.execute(
            '''
            SELECT id, title, message, type, is_read, created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 8
            ''',
            (user_id,),
        )
        notifications = cursor.fetchall()

        return {
            "profile": user,
            "platforms": platforms,
            "policy": policy,
            "recent_claims": recent_claims,
            "notifications": notifications,
        }
    finally:
        cursor.close()
        conn.close()


@app.put("/api/users/{user_id}/profile")
def update_profile(user_id: int, payload: ProfileUpdateInput):
    conn, cursor = dict_cursor()
    try:
        get_user_or_404(cursor, user_id)
        cursor.execute(
            '''
            UPDATE users
            SET full_name = %s, city = %s, zone_name = %s, preferred_hours = %s
            WHERE id = %s
            ''',
            (payload.full_name, payload.city, payload.zone_name, payload.preferred_hours, user_id),
        )
        conn.commit()
        return {"message": "Profile updated successfully"}
    finally:
        cursor.close()
        conn.close()


@app.post("/api/users/{user_id}/platforms")
def add_or_update_platform(user_id: int, payload: PlatformUpdateInput):
    conn, cursor = dict_cursor()
    try:
        get_user_or_404(cursor, user_id)
        cursor.execute(
            '''
            INSERT INTO linked_platforms (user_id, platform, worker_code, trips_completed, avg_hourly_earning)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                worker_code = VALUES(worker_code),
                trips_completed = VALUES(trips_completed),
                avg_hourly_earning = VALUES(avg_hourly_earning),
                status = 'ACTIVE'
            ''',
            (user_id, payload.platform, payload.worker_code, payload.trips_completed, payload.avg_hourly_earning),
        )
        conn.commit()
        return {"message": f"{payload.platform} profile saved successfully"}
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()


@app.post("/api/policies/create")
def create_policy(payload: PolicyInput):
    conn, cursor = dict_cursor()
    try:
        user = get_user_or_404(cursor, payload.user_id)
        cursor.execute(
            '''
            SELECT platform, worker_code, trips_completed, avg_hourly_earning
            FROM linked_platforms
            WHERE user_id = %s AND status = 'ACTIVE'
            ''',
            (payload.user_id,),
        )
        platforms = cursor.fetchall()
        if not platforms:
            raise HTTPException(status_code=400, detail="Add at least one active platform profile before creating a policy")

        premium = calculate_premium_components(user, platforms, payload.plan_name)

        cursor.execute("UPDATE policies SET status = 'PAUSED' WHERE user_id = %s AND status = 'ACTIVE'", (payload.user_id,))
        cursor.execute(
            '''
            INSERT INTO policies (
                user_id, plan_name, base_premium, final_premium, premium_breakdown,
                coverage_hours, max_payout, status, start_date, renewal_date
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE', CURDATE(), DATE_ADD(CURDATE(), INTERVAL 7 DAY))
            ''',
            (
                payload.user_id,
                payload.plan_name,
                premium["base_premium"],
                premium["final_premium"],
                json.dumps(premium["breakdown"]),
                premium["coverage_hours"],
                premium["max_payout"],
            ),
        )

        notify(
            cursor,
            payload.user_id,
            "Policy activated",
            f"{payload.plan_name} Shield is active at ₹{premium['final_premium']}/week.",
            "success",
        )

        conn.commit()
        return {
            "message": "Policy created successfully",
            **premium,
        }
    except HTTPException:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()


@app.get("/api/claims/user/{user_id}")
def get_claims(user_id: int):
    conn, cursor = dict_cursor()
    try:
        get_user_or_404(cursor, user_id)
        cursor.execute(
            '''
            SELECT c.id, c.expected_earnings, c.actual_earnings, c.payout_amount, c.fraud_score,
                   c.claim_status, c.reason, c.created_at,
                   t.trigger_type, t.city, t.zone_name, t.severity
            FROM claims c
            JOIN triggers t ON c.trigger_id = t.id
            WHERE c.user_id = %s
            ORDER BY c.created_at DESC
            ''',
            (user_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


@app.get("/api/notifications/user/{user_id}")
def get_notifications(user_id: int):
    conn, cursor = dict_cursor()
    try:
        get_user_or_404(cursor, user_id)
        cursor.execute(
            '''
            SELECT id, title, message, type, is_read, created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
            ''',
            (user_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


@app.post("/api/admin/triggers")
def create_trigger(payload: TriggerInput):
    conn, cursor = dict_cursor()
    try:
        cursor.execute(
            '''
            INSERT INTO triggers (trigger_type, city, zone_name, severity, description, source, status)
            VALUES (%s, %s, %s, %s, %s, 'manual', 'ACTIVE')
            ''',
            (payload.trigger_type, payload.city, payload.zone_name, payload.severity, payload.description),
        )
        trigger_id = cursor.lastrowid

        cursor.execute(
            '''
            SELECT u.id, u.full_name, u.phone, p.max_payout, p.coverage_hours
            FROM users u
            JOIN policies p ON p.user_id = u.id
            WHERE u.role = 'user'
              AND LOWER(u.city) = LOWER(%s)
              AND LOWER(u.zone_name) = LOWER(%s)
              AND p.status = 'ACTIVE'
            GROUP BY u.id, u.full_name, u.phone, p.max_payout, p.coverage_hours
            ''',
            (payload.city, payload.zone_name),
        )
        users = cursor.fetchall()

        claims_created = []
        for user in users:
            cursor.execute(
                '''
                SELECT AVG(avg_hourly_earning) AS avg_earning, MAX(trips_completed) AS top_trips
                FROM linked_platforms
                WHERE user_id = %s AND status = 'ACTIVE'
                ''',
                (user["id"],),
            )
            stats = cursor.fetchone()
            avg_earning = float(stats["avg_earning"] or 80)
            coverage_hours = int(user["coverage_hours"])
            expected = round(avg_earning * coverage_hours, 2)
            actual = round(expected * 0.15, 2)
            payout = round(min(expected - actual, float(user["max_payout"])), 2)

            recent_claim_penalty = 0.05 if payout < 200 else 0.12
            fraud_score = round(recent_claim_penalty, 2)
            status = "APPROVED"

            try:
                cursor.execute(
                    '''
                    INSERT INTO claims (
                        user_id, trigger_id, expected_earnings, actual_earnings,
                        payout_amount, fraud_score, claim_status, reason
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ''',
                    (
                        user["id"],
                        trigger_id,
                        expected,
                        actual,
                        payout,
                        fraud_score,
                        status,
                        f"{payload.trigger_type} caused a measurable earnings drop in {payload.zone_name}.",
                    ),
                )
            except Exception:
                # unique(user_id, trigger_id) blocks duplicates
                continue

            notify(
                cursor,
                user["id"],
                f"{payload.trigger_type} protection triggered",
                f"Auto-claim approved for ₹{payout} in {payload.zone_name}.",
                "success",
            )
            claims_created.append(
                {
                    "user_id": user["id"],
                    "name": user["full_name"],
                    "phone": user["phone"],
                    "payout": payout,
                }
            )

        conn.commit()
        return {
            "message": "Trigger created and claims processed",
            "trigger_id": trigger_id,
            "claims_created": claims_created,
        }
    except Exception as exc:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        cursor.close()
        conn.close()


@app.get("/api/admin/analytics")
def admin_analytics():
    conn, cursor = dict_cursor()
    try:
        cursor.execute("SELECT COUNT(*) AS total_users FROM users WHERE role = 'user'")
        total_users = cursor.fetchone()["total_users"]

        cursor.execute("SELECT COUNT(*) AS active_policies FROM policies WHERE status = 'ACTIVE'")
        active_policies = cursor.fetchone()["active_policies"]

        cursor.execute("SELECT COUNT(*) AS total_triggers FROM triggers")
        total_triggers = cursor.fetchone()["total_triggers"]

        cursor.execute("SELECT COUNT(*) AS total_claims, COALESCE(SUM(payout_amount), 0) AS total_payout FROM claims")
        claim_stats = cursor.fetchone()

        cursor.execute(
            '''
            SELECT platform, COUNT(*) AS count
            FROM linked_platforms
            GROUP BY platform
            ORDER BY count DESC
            '''
        )
        platform_mix = cursor.fetchall()

        cursor.execute(
            '''
            SELECT t.trigger_type, COUNT(c.id) AS claims_count, COALESCE(SUM(c.payout_amount), 0) AS total_payout
            FROM triggers t
            LEFT JOIN claims c ON c.trigger_id = t.id
            GROUP BY t.trigger_type
            ORDER BY claims_count DESC, t.trigger_type
            '''
        )
        claims_by_trigger = cursor.fetchall()

        cursor.execute(
            '''
            SELECT u.city, COUNT(*) AS users_count
            FROM users u
            WHERE role = 'user'
            GROUP BY u.city
            ORDER BY users_count DESC
            '''
        )
        users_by_city = cursor.fetchall()

        return {
            "summary": {
                "total_users": total_users,
                "active_policies": active_policies,
                "total_triggers": total_triggers,
                "total_claims": claim_stats["total_claims"],
                "total_payout": float(claim_stats["total_payout"] or 0),
            },
            "platform_mix": platform_mix,
            "claims_by_trigger": claims_by_trigger,
            "users_by_city": users_by_city,
        }
    finally:
        cursor.close()
        conn.close()
