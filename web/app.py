from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector as mc

app = Flask(__name__)
app.secret_key = "mysecret"  # change if you like

# ---------- DB CONNECTION ----------

def get_db():
    return mc.connect(
        host="localhost",
        user="root",
        password="root@123",  # <<< CHANGE THIS
        database="VehicleRentalDB"
    )

# ---------- LOGIN / LOGOUT ----------

@app.route("/", methods=["GET", "POST"])
def login():
    message = ""
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if not email or not password:
            message = "Email and Password are required."
            return render_template("login.html", message=message)
        
        cn = get_db()
        cur = cn.cursor(dictionary=True)
        cur.execute("""
            SELECT u.UserID, u.Password, r.RoleName, u.Name
            FROM User u
            LEFT JOIN Role r ON u.RoleID = r.RoleID
            WHERE u.Email = %s
        """, (email,))
        user = cur.fetchone()
        cur.close()
        cn.close()

        if user and user["Password"] == password:
            session["user_id"] = user["UserID"]
            session["role"] = user["RoleName"]
            session["name"] = user["Name"] 
            if user["RoleName"] == "Admin":
                return redirect(url_for("admin_dashboard"))
            elif user["RoleName"] == "Staff":
                return redirect(url_for("staff_dashboard"))
            else:
                return redirect(url_for("customer_dashboard"))
        else:
            message = "Invalid email or password"

    return render_template("login.html", message=message)

@app.route("/register", methods=["GET", "POST"])
def register():
    message = ""
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        # basic validation
        if not name or not email or not password:
            message = "Name, Email, and Password are required."
            return render_template("register.html", message=message)

        cn = get_db()
        cur = cn.cursor(dictionary=True)

        # find RoleID for 'Customer'
        cur.execute("SELECT RoleID FROM Role WHERE RoleName = 'Customer'")
        row = cur.fetchone()
        if row:
            role_id = row["RoleID"]
        else:
            role_id = 3  # fallback if roles are already known

        # try to insert new user
        try:
            cur2 = cn.cursor()
            cur2.execute("""
                INSERT INTO User (Name, Email, Phone, Password, RoleID)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, email, phone, password, role_id))
            cn.commit()
            cur2.close()
            cur.close()
            cn.close()

            # After successful registration, show login page with message
            return render_template("login.html", message="Account created successfully. Please login.")
        except Exception as e:
            # most likely duplicate email or constraint error
            cn.rollback()
            cur.close()
            cn.close()
            message = "Could not create account. Email may already be in use."
            return render_template("register.html", message=message)

    # GET request → show empty form
    return render_template("register.html", message=message)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------- CUSTOMER DASHBOARD (VIEW + RENT + RETURN) ----------

@app.route("/customer")
def customer_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]

    # read filters from query parameters
    f_type = request.args.get("type", "").strip()
    f_model = request.args.get("model", "").strip()
    f_max_price = request.args.get("max_price", "").strip()

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    # build dynamic query for available vehicles
    query = "SELECT * FROM Vehicle WHERE Status = 'Available'"
    params = []

    if f_type:
        query += " AND VehicleType LIKE %s"
        params.append("%" + f_type + "%")
    if f_model:
        query += " AND Model LIKE %s"
        params.append("%" + f_model + "%")
    if f_max_price:
        try:
            max_val = float(f_max_price)
            query += " AND RentalPrice <= %s"
            params.append(max_val)
        except ValueError:
            pass  # ignore invalid price input

    cur.execute(query, params)
    vehicles = cur.fetchall()

    # active rentals for this user (unchanged)
    cur.execute("""
        SELECT r.RentalID, v.Model, v.VehicleType, r.RentalDate,
               r.ReturnDate, r.Status, r.TotalAmount
        FROM Rental r
        JOIN Vehicle v ON r.VehicleID = v.VehicleID
        WHERE r.UserID = %s AND r.Status = 'Active'
    """, (user_id,))
    active_rentals = cur.fetchall()

    cur.close()
    cn.close()

    return render_template(
        "dashboard_customer.html",
        vehicles=vehicles,
        active_rentals=active_rentals,
        f_type=f_type,
        f_model=f_model,
        f_max_price=f_max_price
    )



@app.route("/customer/rent/<int:vehicle_id>", methods=["POST"])
def customer_rent(vehicle_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]

    # get number of days from form (default to 1 if missing/invalid)
    try:
        days = int(request.form.get("days", "1"))
    except ValueError:
        days = 1
    if days < 1:
        days = 1

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    # Get vehicle & price
    cur.execute(
        "SELECT VehicleID, RentalPrice FROM Vehicle WHERE VehicleID=%s AND Status='Available'",
        (vehicle_id,)
    )
    vehicle = cur.fetchone()

    if not vehicle:
        cur.close()
        cn.close()
        return redirect(url_for("customer_dashboard"))

    price_per_day = vehicle["RentalPrice"]
    total = price_per_day * days

    cur2 = cn.cursor()
    cur2.execute("""
        INSERT INTO Rental (UserID, VehicleID, RentalDate, ReturnDate, TotalAmount, Status)
        VALUES (%s, %s, CURDATE(), DATE_ADD(CURDATE(), INTERVAL %s DAY), %s, 'Active')
    """, (user_id, vehicle_id, days, total))

    # you can keep or remove this if you add triggers later
    cur2.execute("UPDATE Vehicle SET Status='Rented' WHERE VehicleID=%s", (vehicle_id,))

    cn.commit()
    cur2.close()
    cur.close()
    cn.close()

    return redirect(url_for("customer_dashboard"))



@app.route("/customer/return/<int:rental_id>")
def customer_return(rental_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    # Get rental and vehicle
    cur.execute("""
        SELECT r.RentalID, r.UserID, r.VehicleID, r.TotalAmount, r.Status
        FROM Rental r
        WHERE r.RentalID = %s
    """, (rental_id,))
    rental = cur.fetchone()

    if not rental or rental["UserID"] != user_id or rental["Status"] != "Active":
        cur.close()
        cn.close()
        return redirect(url_for("customer_dashboard"))

    amount = rental["TotalAmount"]
    vehicle_id = rental["VehicleID"]

    cur2 = cn.cursor()
    # Update rental
    cur2.execute("""
        UPDATE Rental
        SET Status='Completed', ReturnDate = CURDATE()
        WHERE RentalID=%s
    """, (rental_id,))

    # Insert payment (mode fixed as 'Cash' for demo)
    cur2.execute("""
        INSERT INTO Payment (RentalID, PaymentDate, Amount, PaymentMode)
        VALUES (%s, CURDATE(), %s, 'Cash')
    """, (rental_id, amount))

    # Free the vehicle
    cur2.execute("""
        UPDATE Vehicle
        SET Status='Available'
        WHERE VehicleID=%s
    """, (vehicle_id,))

    cn.commit()
    cur2.close()
    cur.close()
    cn.close()

    return redirect(url_for("customer_dashboard"))

@app.route("/customer/payments")
def customer_payments():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    # Payments made by this user (join Rental, Vehicle, Payment)
    cur.execute("""
        SELECT p.PaymentID, p.PaymentDate, p.Amount, p.PaymentMode,
               r.RentalID, v.Model, v.VehicleType
        FROM Payment p
        JOIN Rental r ON p.RentalID = r.RentalID
        JOIN Vehicle v ON r.VehicleID = v.VehicleID
        WHERE r.UserID = %s
        ORDER BY p.PaymentDate DESC
    """, (user_id,))
    payments = cur.fetchall()

    cur.close()
    cn.close()

    return render_template("customer_payments.html", payments=payments)


# ---------- STAFF DASHBOARD (VEHICLE MANAGEMENT) ----------

@app.route("/staff")
def staff_dashboard():
    if "user_id" not in session or session.get("role") not in ("Staff", "Admin"):
        return redirect(url_for("login"))

    f_type = request.args.get("type", "").strip()
    f_model = request.args.get("model", "").strip()
    f_status = request.args.get("status", "").strip()

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    query = "SELECT * FROM Vehicle WHERE 1=1"
    params = []

    if f_type:
        query += " AND VehicleType LIKE %s"
        params.append("%" + f_type + "%")
    if f_model:
        query += " AND Model LIKE %s"
        params.append("%" + f_model + "%")
    if f_status:
        query += " AND Status = %s"
        params.append(f_status)

    cur.execute(query, params)
    vehicles = cur.fetchall()
    cur.close()
    cn.close()

    return render_template(
        "dashboard_staff.html",
        vehicles=vehicles,
        f_type=f_type,
        f_model=f_model,
        f_status=f_status
    )



@app.route("/staff/vehicle/<int:vehicle_id>/status", methods=["POST"])
def staff_update_status(vehicle_id):
    if "user_id" not in session or session.get("role") not in ("Staff", "Admin"):
        return redirect(url_for("login"))

    new_status = request.form.get("status")

    if new_status not in ("Available", "Rented", "Maintenance"):
        return redirect(url_for("staff_dashboard"))

    cn = get_db()
    cur = cn.cursor()
    cur.execute("UPDATE Vehicle SET Status=%s WHERE VehicleID=%s", (new_status, vehicle_id))
    cn.commit()
    cur.close()
    cn.close()

    return redirect(url_for("staff_dashboard"))

# ---------- ADMIN DASHBOARD (USER MANAGEMENT + REPORTS LINK) ----------

@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    # Users + roles
    cur.execute("""
        SELECT u.UserID, u.Name, u.Email, r.RoleName, u.RoleID
        FROM User u
        LEFT JOIN Role r ON u.RoleID = r.RoleID
    """)
    users = cur.fetchall()

    # roles for dropdown
    cur.execute("SELECT RoleID, RoleName FROM Role")
    roles = cur.fetchall()

    cur.close()
    cn.close()

    return render_template("dashboard_admin.html", users=users, roles=roles)


@app.route("/admin/user/<int:user_id>/set_role", methods=["POST"])
def admin_set_role(user_id):
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    role_id = request.form.get("role_id")

    cn = get_db()
    cur = cn.cursor()
    cur.execute("UPDATE User SET RoleID=%s WHERE UserID=%s", (role_id, user_id))
    cn.commit()
    cur.close()
    cn.close()

    return redirect(url_for("admin_dashboard"))

@app.route("/admin/users/add", methods=["GET", "POST"])
def admin_add_user():
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    # get roles for dropdown
    cur.execute("SELECT RoleID, RoleName FROM Role")
    roles = cur.fetchall()

    message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        role_id = request.form.get("role_id")

        if not name or not email or not password:
            message = "Name, Email and Password are required."
            return render_template("admin_add_user.html", roles=roles, message=message)

        try:
            cur2 = cn.cursor()
            cur2.execute("""
                INSERT INTO User (Name, Email, Phone, Password, RoleID)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, email, phone, password, role_id))
            cn.commit()
            cur2.close()
            cur.close()
            cn.close()
            return redirect(url_for("admin_dashboard"))
        except Exception:
            cn.rollback()
            message = "Could not create user (email may already exist)."
            cur.close()
            cn.close()
            return render_template("admin_add_user.html", roles=roles, message=message)

    cur.close()
    cn.close()
    return render_template("admin_add_user.html", roles=roles, message=message)

@app.route("/admin/users/edit/<int:user_id>", methods=["GET", "POST"])
def admin_edit_user(user_id):
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    # fetch roles
    cur.execute("SELECT RoleID, RoleName FROM Role")
    roles = cur.fetchall()

    # fetch user
    cur.execute("SELECT * FROM User WHERE UserID = %s", (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        cn.close()
        return redirect(url_for("admin_dashboard"))

    message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        role_id = request.form.get("role_id")

        if not name or not email:
            message = "Name and Email are required."
            return render_template("admin_edit_user.html", user=user, roles=roles, message=message)

        try:
            cur2 = cn.cursor()
            # if password left blank, keep the old one
            if password:
                cur2.execute("""
                    UPDATE User
                    SET Name=%s, Email=%s, Phone=%s, Password=%s, RoleID=%s
                    WHERE UserID=%s
                """, (name, email, phone, password, role_id, user_id))
            else:
                cur2.execute("""
                    UPDATE User
                    SET Name=%s, Email=%s, Phone=%s, RoleID=%s
                    WHERE UserID=%s
                """, (name, email, phone, role_id, user_id))

            cn.commit()
            cur2.close()
            cur.close()
            cn.close()
            return redirect(url_for("admin_dashboard"))
        except Exception:
            cn.rollback()
            message = "Could not update user (email may already exist)."
            cur.close()
            cn.close()
            return render_template("admin_edit_user.html", user=user, roles=roles, message=message)

    cur.close()
    cn.close()
    return render_template("admin_edit_user.html", user=user, roles=roles, message=message)

@app.route("/admin/users/delete/<int:user_id>")
def admin_delete_user(user_id):
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    # (optional) prevent admin from deleting their own account
    if user_id == session.get("user_id"):
        return redirect(url_for("admin_dashboard"))

    cn = get_db()
    cur = cn.cursor()

    try:
        cur.execute("DELETE FROM User WHERE UserID=%s", (user_id,))
        cn.commit()
    except Exception:
        cn.rollback()
    finally:
        cur.close()
        cn.close()

    return redirect(url_for("admin_dashboard"))

# ---------- ADMIN REPORTS ----------

@app.route("/admin/reports")
def admin_reports():
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    # simple stats
    cur.execute("SELECT COUNT(*) AS total_users FROM User")
    total_users = cur.fetchone()["total_users"]

    cur.execute("SELECT COUNT(*) AS total_vehicles FROM Vehicle")
    total_vehicles = cur.fetchone()["total_vehicles"]

    cur.execute("SELECT COUNT(*) AS total_rentals FROM Rental")
    total_rentals = cur.fetchone()["total_rentals"]

    cur.execute("SELECT IFNULL(SUM(Amount),0) AS total_revenue FROM Payment")
    total_revenue = cur.fetchone()["total_revenue"]

    # recent rentals
        # recent rentals
    cur.execute("""
        SELECT r.RentalID, u.Name AS Customer, v.Model,
               r.RentalDate, r.ReturnDate, r.Status, r.TotalAmount
        FROM Rental r
        JOIN User u ON r.UserID = u.UserID
        JOIN Vehicle v ON r.VehicleID = v.VehicleID
        ORDER BY r.RentalDate DESC
        LIMIT 10
    """)
    rentals = cur.fetchall()

    # recent payments
    cur.execute("""
        SELECT PaymentID, RentalID, PaymentDate, Amount, PaymentMode
        FROM Payment
        ORDER BY PaymentDate DESC
        LIMIT 10
    """)
    payments = cur.fetchall()

    cur.close()
    cn.close()

    return render_template(
        "admin_reports.html",
        total_users=total_users,
        total_vehicles=total_vehicles,
        total_rentals=total_rentals,
        total_revenue=total_revenue,
        rentals=rentals,
        payments=payments
    )

@app.route("/admin/vehicles")
def admin_vehicles():
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    cn = get_db()
    cur = cn.cursor(dictionary=True)
    cur.execute("SELECT * FROM Vehicle")
    vehicles = cur.fetchall()
    cur.close()
    cn.close()

    return render_template("admin_vehicles.html", vehicles=vehicles)

@app.route("/admin/vehicles/add", methods=["GET", "POST"])
def admin_add_vehicle():
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        vtype = request.form["vehicle_type"]
        model = request.form["model"]
        regno = request.form["regno"]
        price = request.form["price"]

        cn = get_db()
        cur = cn.cursor()
        cur.execute("""
            INSERT INTO Vehicle (VehicleType, Model, RegistrationNumber, RentalPrice, Status)
            VALUES (%s, %s, %s, %s, 'Available')
        """, (vtype, model, regno, price))
        cn.commit()
        cur.close()
        cn.close()

        return redirect(url_for("admin_vehicles"))

    return render_template("admin_add_vehicle.html")

@app.route("/admin/vehicles/edit/<int:vehicle_id>", methods=["GET", "POST"])
def admin_edit_vehicle(vehicle_id):
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    if request.method == "POST":
        vtype = request.form["vehicle_type"]
        model = request.form["model"]
        regno = request.form["regno"]
        price = request.form["price"]
        status = request.form["status"]

        cur2 = cn.cursor()
        cur2.execute("""
            UPDATE Vehicle
            SET VehicleType=%s, Model=%s, RegistrationNumber=%s,
                RentalPrice=%s, Status=%s
            WHERE VehicleID=%s
        """, (vtype, model, regno, price, status, vehicle_id))

        cn.commit()
        cur2.close()
        cur.close()
        cn.close()
        return redirect(url_for("admin_vehicles"))

    # GET → load vehicle data
    cur.execute("SELECT * FROM Vehicle WHERE VehicleID=%s", (vehicle_id,))
    vehicle = cur.fetchone()
    cur.close()
    cn.close()

    return render_template("admin_edit_vehicle.html", vehicle=vehicle)

@app.route("/admin/vehicles/delete/<int:vehicle_id>")
def admin_delete_vehicle(vehicle_id):
    if "user_id" not in session or session.get("role") != "Admin":
        return redirect(url_for("login"))

    cn = get_db()
    cur = cn.cursor()

    cur.execute("DELETE FROM Vehicle WHERE VehicleID=%s", (vehicle_id,))
    cn.commit()

    cur.close()
    cn.close()

    return redirect(url_for("admin_vehicles"))

@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    cn = get_db()
    cur = cn.cursor(dictionary=True)

    # fetch current user info
    cur.execute("SELECT UserID, Name, Email, Phone FROM User WHERE UserID = %s", (user_id,))
    user = cur.fetchone()

    if not user:
        cur.close()
        cn.close()
        return redirect(url_for("login"))

    message = ""

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email:
            message = "Name and Email are required."
            return render_template("profile.html", user=user, message=message)

        try:
            cur2 = cn.cursor()
            if password:
                cur2.execute("""
                    UPDATE User
                    SET Name=%s, Email=%s, Phone=%s, Password=%s
                    WHERE UserID=%s
                """, (name, email, phone, password, user_id))
            else:
                cur2.execute("""
                    UPDATE User
                    SET Name=%s, Email=%s, Phone=%s
                    WHERE UserID=%s
                """, (name, email, phone, user_id))

            cn.commit()
            cur2.close()

            # refresh user data
            cur.execute("SELECT UserID, Name, Email, Phone FROM User WHERE UserID = %s", (user_id,))
            user = cur.fetchone()
            message = "Profile updated successfully."
        except Exception:
            cn.rollback()
            message = "Could not update profile (email may be in use)."

    cur.close()
    cn.close()
    return render_template("profile.html", user=user, message=message)


# ---------- MAIN ----------

if __name__ == "__main__":
    app.run(debug=True)
