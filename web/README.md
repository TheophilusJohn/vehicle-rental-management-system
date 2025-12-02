
# 🚗 Vehicle Rental Management System (VRMS)
A full-stack **Vehicle Rental Management System** built using **Flask**, **MySQL**, and **Bootstrap**.  
This system supports **role-based access**, **vehicle rental workflows**, **user & vehicle management**, **reporting**, **filters**, and **payments**.

> Designed as a DBMS course project demonstrating real-world database design, SQL, triggers, procedures, and full CRUD operations.

## 📌 Table of Contents
- Features
- Tech Stack
- System Architecture
- Database Design
- Screenshots
- Installation Guide
- How to Run the Project
- Project Structure
- Demo Users
- Future Improvements
- Authors

# ⭐ Features

## 🔐 User Roles
| Role | Capabilities |
|------|--------------|
| **Customer** | Register/Login, Search/Filter vehicles, Rent/Return vehicles, View payment history, Update profile |
| **Staff** | View all vehicles, Update vehicle status (Available/Rented/Maintenance), Filter vehicles |
| **Admin** | Full CRUD on Users & Vehicles, Assign roles, Override system records, View reports (revenue, totals, recent activity) |

## 🚗 Vehicle Management
- Add / Edit / Delete vehicles (Admin)
- Update status (Staff & Admin)
- Search & filter by type, model, price, status

## 📅 Rental Workflow
- Rent vehicle for **N days**
- Auto total amount calculation
- Triggers auto-update vehicle status
- Returning vehicle generates payment

## 💳 Payment System
- Auto payment creation on return
- Admin sees all revenue
- Customer sees payment history

## 👤 Profile Management
All users can update name, email, phone, password.

## 📊 Admin Reports
- Total users  
- Total vehicles  
- Total rentals  
- Total revenue  
- Recent payments  
- Recent rentals  

# 🛠 Tech Stack
- **Backend:** Flask (Python)
- **Frontend:** HTML, Bootstrap
- **Database:** MySQL
- **Tools:** VS Code, MySQL Workbench, Git

# 🧩 System Architecture
```
Customer ──┐
Staff    ──┼──▶ Flask Backend ▶ MySQL DB
Admin    ──┘         ▲
                     │
                     └── HTML/Bootstrap Frontend
```

# 🗄 Database Design
### Main Tables:
User, Role, Vehicle, Rental, Payment

### Triggers:
- Set vehicle status on rental insert/update

### Stored Procedure:
- `sp_book_vehicle`

### Export:
Located at: `/db/vrms_export.sql`

# 🚀 Installation Guide
### 1. Clone repo:
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd vrms_project/web
```

### 2. Create environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies:
```bash
pip install -r requirements.txt
```

### 4. Import database:
Use MySQL Workbench to import `db/vrms_export.sql`.

### 5. Update DB credentials in `app.py`.

### 6. Run app:
```bash
python3 app.py
```

# 📁 Project Structure
```
vrms_project/
  web/
    app.py
    templates/
    requirements.txt
  db/
    vrms_export.sql
  README.md
  .gitignore
```

# 👥 Demo Users
| Role | Email | Password |
|------|--------|----------|
| Admin | admin1@vrms.com | pass |
| Staff | staff1@vrms.com | pass |
| Customer | alice@vrms.com | pass |

# 🔮 Future Improvements
- Hashed passwords
- Online payment gateway
- Vehicle images
- Email notifications
- Multi-branch feature

# 👨‍💻 Authors
**Theophilus Biju John**
