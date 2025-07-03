
# QuickDeliverLite

QuickDeliverLite is a simple Flask web app for managing delivery requests. Customers can request deliveries, drivers can accept and update status, and admins can monitor the system.

---

## 📦 Installation

1. Clone this repo:
   ```bash
   git clone https://github.com/Khayyum-Abdul/Quickdeliverlite-47.git
   cd Quickdeliverlite-47
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

3. Activate it:
   - PowerShell: `.env\Scripts\Activate.ps1`
   - CMD: `venv\Scriptsctivate.bat`
   - Mac/Linux: `source venv/bin/activate`

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Create a `.env` file and add:
   ```
   SECRET_KEY=your_secret_key
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASS=your_gmail_app_password
   ```

---

## 🚀 Usage

1. Run the app:
   ```bash
   flask run
   ```

2. Open in browser:
   ```
   http://127.0.0.1:5000
   ```

3. To create an admin user:

   ```python
   from app import app, db
   from models import User
   from werkzeug.security import generate_password_hash

   with app.app_context():
       admin = User(
           name="Admin",
           email="admin@example.com",
           password=generate_password_hash("adminpasswordak47"),
           role="Admin"
       )
       db.session.add(admin)
       db.session.commit()
   ```

---

## 📁 Folder Structure

```
Quickdeliverlite-47/
├── app.py
├── models.py
├── templates/
├── requirements.txt
├── .env
└── README.md
```

---

## 👤 Author

**Abdul Khayyum**  
GitHub: [@Khayyum-Abdul](https://github.com/Khayyum-Abdul)

---

## 🔗 Live Demo

Try it here:  
👉 [https://KhayyumAbdul.pythonanywhere.com](https://KhayyumAbdul.pythonanywhere.com)

---
