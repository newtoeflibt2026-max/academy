import os
ADMIN_IDS=[5602495831,469136626,5572314718]
BOT_TOKEN=os.environ.get("BOT_TOKEN","")
DATABASE_PATH=os.path.join(os.path.dirname(os.path.abspath(__file__)),"data","yamen_academy.db")
WEBAPP_PORT=int(os.environ.get("PORT",8080))
print(f"⚙️ يامن أكاديمي Config | Admin:{ADMIN_IDS[0]} | Port:{WEBAPP_PORT}")
