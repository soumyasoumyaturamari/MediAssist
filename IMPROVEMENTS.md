MediAssist improvements
=======================

- Doctors can open patient medical records from completed appointments.
- Patients can use Print Medical Records on the Medical History page (opens the browser print dialog; choose Save as PDF if desired).
- Django admin branding now says Administration. The admin index has separate Add Appointment, Add Doctor, and Add Medical Record shortcuts.
- Admin appointment and doctor availability times display and accept HH:MM without seconds. The Add Appointment status selector offers Cancelled and Completed.
- Existing medical records are read-only in admin; admins can view them and can add a new record from the shortcut.
- Doctor passwords created through Django admin are hashed in the same format used by doctor login.

Setup
-----
1. Create/activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and add any required environment values.
4. Run `python manage.py migrate` and `python manage.py runserver`.

The original `.env` file is intentionally not included in this archive to avoid redistributing API keys or other secrets.


Follow-up fixes (30 September 2026)
- Doctor medical-record viewing supports legacy appointments whose doctor foreign key is empty but whose stored doctor name matches the logged-in doctor.
- Appointment status in Django admin now offers only Completed and Cancelled, with a blank prompt to require an explicit choice. The main app retains its full workflow statuses.
- Add Appointment, Add Doctor, and Add Patient are available from the changelist Action dropdown; their top-right add buttons are hidden on those three pages. Selecting the add action opens the relevant add form directly.
