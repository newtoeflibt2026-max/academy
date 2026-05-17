"""Yamen Academy - Admin API Web (Safe)"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import sys, os, traceback

admin_api_web_bp = Blueprint("admin_api_web", __name__, url_prefix="/api/admin")

def _q(query, args=(), one=False):
    try:
        from modules.models import query_db
        return query_db(query, args, one=one)
    except:
        import sqlite3
        db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "yamen_academy.db")
        conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row
        cur = conn.execute(query, args); rv = cur.fetchall(); cur.close(); conn.close()
        return (rv[0] if rv else None) if one else rv

def _db():
    try:
        from modules.models import get_db
        return get_db()
    except:
        import sqlite3
        db = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "yamen_academy.db")
        conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row
        return conn

@admin_api_web_bp.route("/stats")
def stats():
    try:
        ts = _q("SELECT COUNT(*) as cnt FROM students", one=True)
        ac = _q("SELECT COUNT(*) as cnt FROM students WHERE is_active=1", one=True)
        pp = _q("SELECT COUNT(*) as cnt FROM payments WHERE status='pending'", one=True)
        return jsonify({"success":True,"data":{
            "total_students": ts["cnt"] if ts else 0,
            "active_students": ac["cnt"] if ac else 0,
            "pending_payments": pp["cnt"] if pp else 0
        }})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}), 500

@admin_api_web_bp.route("/students")
def students():
    try:
        rows = _q("""SELECT s.id,s.name,s.path,s.target_band,s.days_available,s.is_active,
            COALESCE(p.band,'N/A') as placement_band,COALESCE(p.level,'N/A') as placement_level
            FROM students s LEFT JOIN placement_results p ON p.student_id=s.id
            AND p.id=(SELECT MAX(id) FROM placement_results WHERE student_id=s.id) ORDER BY s.id DESC""")
        return jsonify({"success":True,"data":[dict(r) for r in rows] if rows else []})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}), 500

@admin_api_web_bp.route("/student/toggle_active/<int:sid>", methods=["POST"])
def toggle(sid):
    try:
        c = _q("SELECT is_active FROM students WHERE id=?",(sid,),one=True)
        if not c: return jsonify({"success":False,"error":"Not found"}),404
        ns = 0 if c["is_active"] else 1
        db = _db(); db.execute("UPDATE students SET is_active=? WHERE id=?",(ns,sid)); db.commit()
        return jsonify({"success":True,"message":f"Student {sid} {'activated' if ns else 'deactivated'}"})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}), 500

@admin_api_web_bp.route("/student/extend_subscription", methods=["POST"])
def extend():
    try:
        data = request.get_json(force=True)
        sid, days = data.get("student_id"), int(data.get("days",0))
        if not sid or days <= 0: return jsonify({"success":False,"error":"student_id and days required"}),400
        st = _q("SELECT * FROM students WHERE id=?",(sid,),one=True)
        if not st: return jsonify({"success":False,"error":"Not found"}),404
        nd = (st.get("days_available",0) or 0) + days
        db = _db(); db.execute("UPDATE students SET days_available=?,is_active=1 WHERE id=?",(nd,sid)); db.commit()
        return jsonify({"success":True,"message":f"+{days} days (total: {nd})"})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}), 500

@admin_api_web_bp.route("/payments/pending")
def pending():
    try:
        rows = _q("""SELECT p.id,p.student_id,s.name as student_name,p.plan,p.amount,
            p.payment_method,p.status,p.created_at FROM payments p
            LEFT JOIN students s ON s.id=p.student_id WHERE p.status='pending' ORDER BY p.created_at DESC""")
        return jsonify({"success":True,"data":[dict(r) for r in rows] if rows else []})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}), 500

@admin_api_web_bp.route("/payment/approve/<int:pid>", methods=["POST"])
def approve(pid):
    try:
        p = _q("SELECT * FROM payments WHERE id=?",(pid,),one=True)
        if not p: return jsonify({"success":False,"error":"Not found"}),404
        db = _db()
        db.execute("UPDATE payments SET status='approved' WHERE id=?",(pid,))
        db.execute("UPDATE students SET is_active=1 WHERE id=?",(p["student_id"],))
        dur = {"flexible":30,"emergency":30,"excellence":90}.get(p.get("plan",""),30)
        exp = (datetime.now() + timedelta(days=dur)).strftime("%Y-%m-%d")
        ex = _q("SELECT id FROM subscriptions WHERE student_id=? AND plan=?",(p["student_id"],p.get("plan")),one=True)
        if ex:
            db.execute("UPDATE subscriptions SET is_active=1,expiry_date=? WHERE id=?",(exp,ex["id"]))
        else:
            db.execute("INSERT INTO subscriptions (student_id,plan,is_active,expiry_date,created_at) VALUES (?,?,1,?,?)",
                       (p["student_id"],p.get("plan"),exp,datetime.now().isoformat()))
        db.commit()
        return jsonify({"success":True,"message":f"Payment #{pid} approved"})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}), 500

@admin_api_web_bp.route("/payment/reject/<int:pid>", methods=["POST"])
def reject(pid):
    try:
        if not _q("SELECT id FROM payments WHERE id=?",(pid,),one=True):
            return jsonify({"success":False,"error":"Not found"}),404
        db = _db(); db.execute("UPDATE payments SET status='rejected' WHERE id=?",(pid,)); db.commit()
        return jsonify({"success":True,"message":f"Payment #{pid} rejected"})
    except Exception as e:
        return jsonify({"success":False,"error":str(e)}), 500
