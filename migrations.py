from app import create_app, db
from sqlalchemy import text, inspect

app = create_app()
with app.app_context():
    inspector = inspect(db.engine)

    # ── Assets columns ──────────────────────────────────────────────────────
    existing_assets = [c['name'] for c in inspector.get_columns('assets')]
    asset_columns = [
        ("site_name",          "VARCHAR(150)"),
        ("team_leader",        "VARCHAR(100)"),
        ("previous_users",     "VARCHAR(255)"),
        ("designation",        "VARCHAR(100)"),
        ("cpu_model",          "VARCHAR(150)"),
        ("cpu_serial",         "VARCHAR(100)"),
        ("motherboard",        "VARCHAR(150)"),
        ("ssd_model",          "VARCHAR(150)"),
        ("internal_hdd",       "VARCHAR(100)"),
        ("operating_system",   "VARCHAR(100)"),
        ("full_serial_number", "VARCHAR(150)"),
        ("ram_details",        "VARCHAR(100)"),
        ("ram_type",           "VARCHAR(50)"),
        ("monitor_model",      "VARCHAR(150)"),
        ("mouse_model",        "VARCHAR(150)"),
        ("keyboard_model",     "VARCHAR(150)"),
        ("remarks",            "TEXT"),
    ]
    for col_name, col_type in asset_columns:
        if col_name not in existing_assets:
            db.session.execute(text(f"ALTER TABLE assets ADD COLUMN `{col_name}` {col_type} NULL"))
            print(f"  Added assets.{col_name}")
        else:
            print(f"  Exists assets.{col_name}")

    # ── Tickets columns ──────────────────────────────────────────────────────
    existing_tickets = [c['name'] for c in inspector.get_columns('tickets')]
    ticket_columns = [
        ("ticket_number",    "VARCHAR(20)"),
        ("source",           "ENUM('manual','email','phone','walk_in','self_service') NOT NULL DEFAULT 'manual'"),
        ("email_message_id", "VARCHAR(255)"),
        ("email_from",       "VARCHAR(255)"),
        ("email_to",         "VARCHAR(255)"),
        ("email_cc",         "VARCHAR(500)"),
        ("email_subject",    "VARCHAR(255)"),
        ("parent_ticket_id", "INT"),
        ("is_auto_generated","TINYINT(1) NOT NULL DEFAULT 0"),
        ("sub_category",     "VARCHAR(100)"),
        ("impact",           "ENUM('low','medium','high') NOT NULL DEFAULT 'medium'"),
        ("urgency",          "ENUM('low','medium','high') NOT NULL DEFAULT 'medium'"),
        ("support_group",    "VARCHAR(100)"),
        ("tags",             "VARCHAR(255)"),
        ("due_date",         "DATETIME"),
        ("software_id",      "INT"),
    ]
    for col_name, col_type in ticket_columns:
        if col_name not in existing_tickets:
            db.session.execute(text(f"ALTER TABLE tickets ADD COLUMN `{col_name}` {col_type} NULL"))
            print(f"  Added tickets.{col_name}")
        else:
            print(f"  Exists tickets.{col_name}")

    # Back-fill ticket_number for existing rows
    db.session.execute(text(
        "UPDATE tickets SET ticket_number = CONCAT('HD', LPAD(id, 5, '0')) WHERE ticket_number IS NULL"
    ))



    # Email config inbound columns
    existing_email_config = [c['name'] for c in inspector.get_columns('email_config')]
    email_config_columns = [
        ("inbound_enabled", "TINYINT(1) NOT NULL DEFAULT 0"),
        ("imap_server",     "VARCHAR(120)"),
        ("imap_port",       "INT DEFAULT 993"),
        ("imap_use_ssl",    "TINYINT(1) NOT NULL DEFAULT 1"),
        ("imap_username",   "VARCHAR(120)"),
        ("imap_password",   "VARCHAR(255)"),
        ("imap_folder",     "VARCHAR(80) DEFAULT 'INBOX'"),
        ("imap_last_uid",   "INT"),
        ("signature_enabled", "TINYINT(1) NOT NULL DEFAULT 1"),
        ("auto_insert_signature", "TINYINT(1) NOT NULL DEFAULT 1"),
        ("signature_html", "TEXT"),
    ]
    for col_name, col_type in email_config_columns:
        if col_name not in existing_email_config:
            db.session.execute(text(f"ALTER TABLE email_config ADD COLUMN `{col_name}` {col_type} NULL"))
            print(f"  Added email_config.{col_name}")
        else:
            print(f"  Exists email_config.{col_name}")

    existing_users = [c['name'] for c in inspector.get_columns('users')]
    try:
        db.session.execute(text("""
            ALTER TABLE users MODIFY COLUMN role
            ENUM('admin','staff','hr','moder','master_admin','admin_staff','hr_admin','hr_staff','user')
            NOT NULL DEFAULT 'user'
        """))
        db.session.execute(text("UPDATE users SET role = 'master_admin' WHERE role = 'admin'"))
        db.session.execute(text("UPDATE users SET role = 'admin_staff' WHERE role = 'staff'"))
        db.session.execute(text("UPDATE users SET role = 'hr_admin' WHERE role = 'hr'"))
        db.session.execute(text("UPDATE users SET role = 'hr_staff' WHERE role = 'moder'"))
        db.session.execute(text("""
            ALTER TABLE users MODIFY COLUMN role
            ENUM('master_admin','admin_staff','hr_admin','hr_staff','user')
            NOT NULL DEFAULT 'user'
        """))
        print("  Updated users.role enum and migrated role values")
    except Exception as exc:
        print(f"  Skipped users.role enum update: {exc}")
    user_columns = [
        ("company_domain", "VARCHAR(120)"),
        ("employment_type", "VARCHAR(40)"),
        ("work_location", "VARCHAR(120)"),
        ("branch", "VARCHAR(120)"),
        ("cost_center", "VARCHAR(80)"),
        ("grade", "VARCHAR(60)"),
        ("shift", "VARCHAR(80)"),
        ("probation_end_date", "DATE"),
        ("emergency_contact_name", "VARCHAR(100)"),
        ("emergency_contact_phone", "VARCHAR(30)"),
        ("allow_helpdesk_admin", "TINYINT(1) NOT NULL DEFAULT 0"),
        ("allow_inventory", "TINYINT(1) NOT NULL DEFAULT 0"),
        ("allow_licenses", "TINYINT(1) NOT NULL DEFAULT 0"),
        ("allow_compliance", "TINYINT(1) NOT NULL DEFAULT 0"),
    ]
    for col_name, col_type in user_columns:
        if col_name not in existing_users:
            db.session.execute(text(f"ALTER TABLE users ADD COLUMN `{col_name}` {col_type} NULL"))
            print(f"  Added users.{col_name}")
        else:
            print(f"  Exists users.{col_name}")
    db.session.execute(text("""
        UPDATE users
        SET company_domain = 'Winsoft'
        WHERE (company_domain IS NULL OR company_domain = '')
          AND (username IS NULL OR username != 'system_email_requester')
    """))
    print("  Back-filled missing users.company_domain with Winsoft")

    from app.utils.departments import STANDARD_DEPARTMENTS

    existing_departments = {
        row[0]: row[1] for row in db.session.execute(text("SELECT LOWER(name), id FROM departments")).all()
    }
    for department in STANDARD_DEPARTMENTS:
        department_name = department["name"]
        aliases = [alias.lower() for alias in department["aliases"]]
        department_id = existing_departments.get(department_name.lower())
        if not department_id:
            department_id = next((existing_departments.get(alias) for alias in aliases if existing_departments.get(alias)), None)
        if not department_id:
            db.session.execute(text("""
                INSERT INTO departments (name, description, location, created_at)
                VALUES (:name, :description, :location, NOW())
            """), {
                "name": department_name,
                "description": department["description"],
                "location": department["location"],
            })
            existing_departments[department_name.lower()] = department_name
            print(f"  Created department {department_name}")
        else:
            db.session.execute(text("""
                UPDATE departments
                SET name = :name, description = :description, location = :location
                WHERE id = :department_id
            """), {
                "department_id": department_id,
                "name": department_name,
                "description": department["description"],
                "location": department["location"],
            })
            print(f"  Updated department group {department_name}")

    if not inspector.has_table('user_signatures'):
        db.session.execute(text("""
            CREATE TABLE user_signatures (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                signature_enabled TINYINT(1) NOT NULL DEFAULT 1,
                auto_insert_signature TINYINT(1) NOT NULL DEFAULT 1,
                signature_html TEXT NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_user_signatures_user
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """))
        print("  Created user_signatures")
    else:
        print("  Exists user_signatures")

    existing_articles = [c['name'] for c in inspector.get_columns('knowledge_articles')]
    article_columns = [
        ("article_type", "VARCHAR(60) NOT NULL DEFAULT 'how_to'"),
        ("summary", "VARCHAR(300)"),
        ("tags", "VARCHAR(255)"),
        ("visibility", "VARCHAR(30) NOT NULL DEFAULT 'all'"),
        ("review_date", "DATE"),
        ("policy_version", "VARCHAR(40)"),
        ("effective_date", "DATE"),
        ("requires_acknowledgement", "TINYINT(1) NOT NULL DEFAULT 0"),
        ("is_featured", "TINYINT(1) NOT NULL DEFAULT 0"),
        ("view_count", "INT NOT NULL DEFAULT 0"),
        ("helpful_count", "INT NOT NULL DEFAULT 0"),
        ("not_helpful_count", "INT NOT NULL DEFAULT 0"),
    ]
    for col_name, col_type in article_columns:
        if col_name not in existing_articles:
            db.session.execute(text(f"ALTER TABLE knowledge_articles ADD COLUMN `{col_name}` {col_type} NULL"))
            print(f"  Added knowledge_articles.{col_name}")
        else:
            print(f"  Exists knowledge_articles.{col_name}")

    if not inspector.has_table('knowledge_attachments'):
        db.session.execute(text("""
            CREATE TABLE knowledge_attachments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                article_id INT NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                stored_filename VARCHAR(255) NOT NULL,
                content_type VARCHAR(120) NULL,
                file_size INT NULL,
                uploaded_by INT NULL,
                created_at DATETIME NULL,
                CONSTRAINT fk_knowledge_attachments_article
                    FOREIGN KEY (article_id) REFERENCES knowledge_articles(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_knowledge_attachments_user
                    FOREIGN KEY (uploaded_by) REFERENCES users(id)
                    ON DELETE SET NULL
            )
        """))
        print("  Created knowledge_attachments")
    else:
        print("  Exists knowledge_attachments")

    if not inspector.has_table('knowledge_acknowledgements'):
        db.session.execute(text("""
            CREATE TABLE knowledge_acknowledgements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                article_id INT NOT NULL,
                user_id INT NOT NULL,
                policy_version VARCHAR(40) NULL,
                acknowledged_at DATETIME NOT NULL,
                UNIQUE KEY uq_knowledge_ack_article_user (article_id, user_id),
                CONSTRAINT fk_knowledge_ack_article
                    FOREIGN KEY (article_id) REFERENCES knowledge_articles(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_knowledge_ack_user
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """))
        print("  Created knowledge_acknowledgements")
    else:
        print("  Exists knowledge_acknowledgements")

    if not inspector.has_table('audit_policies'):
        db.session.execute(text("""
            CREATE TABLE audit_policies (
                id INT AUTO_INCREMENT PRIMARY KEY,
                code VARCHAR(40) NOT NULL UNIQUE,
                title VARCHAR(200) NOT NULL,
                category VARCHAR(80) NULL,
                risk_level VARCHAR(20) NOT NULL DEFAULT 'medium',
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                version VARCHAR(30) NOT NULL DEFAULT '1.0',
                owner_id INT NULL,
                description TEXT NULL,
                scope TEXT NULL,
                controls TEXT NULL,
                effective_date DATE NULL,
                review_date DATE NULL,
                requires_acknowledgement TINYINT(1) NOT NULL DEFAULT 0,
                created_by INT NULL,
                created_at DATETIME NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_audit_policies_owner
                    FOREIGN KEY (owner_id) REFERENCES users(id)
                    ON DELETE SET NULL,
                CONSTRAINT fk_audit_policies_creator
                    FOREIGN KEY (created_by) REFERENCES users(id)
                    ON DELETE SET NULL
            )
        """))
        print("  Created audit_policies")
    else:
        print("  Exists audit_policies")

    if not inspector.has_table('audit_policy_acknowledgements'):
        db.session.execute(text("""
            CREATE TABLE audit_policy_acknowledgements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                policy_id INT NOT NULL,
                user_id INT NOT NULL,
                policy_version VARCHAR(30) NULL,
                acknowledged_at DATETIME NOT NULL,
                UNIQUE KEY uq_audit_policy_ack_policy_user (policy_id, user_id),
                CONSTRAINT fk_audit_policy_ack_policy
                    FOREIGN KEY (policy_id) REFERENCES audit_policies(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_audit_policy_ack_user
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """))
        print("  Created audit_policy_acknowledgements")
    else:
        print("  Exists audit_policy_acknowledgements")

    if not inspector.has_table('audit_policy_attachments'):
        db.session.execute(text("""
            CREATE TABLE audit_policy_attachments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                policy_id INT NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                stored_filename VARCHAR(255) NOT NULL,
                content_type VARCHAR(120) NULL,
                file_size INT NULL,
                uploaded_by INT NULL,
                created_at DATETIME NULL,
                CONSTRAINT fk_audit_policy_attachments_policy
                    FOREIGN KEY (policy_id) REFERENCES audit_policies(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_audit_policy_attachments_user
                    FOREIGN KEY (uploaded_by) REFERENCES users(id)
                    ON DELETE SET NULL
            )
        """))
        print("  Created audit_policy_attachments")
    else:
        print("  Exists audit_policy_attachments")

    if not inspector.has_table('audit_plans'):
        db.session.execute(text("""
            CREATE TABLE audit_plans (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(200) NOT NULL,
                audit_type VARCHAR(40) NOT NULL DEFAULT 'internal',
                status VARCHAR(30) NOT NULL DEFAULT 'planned',
                policy_id INT NULL,
                auditor_id INT NULL,
                department_id INT NULL,
                scope TEXT NULL,
                scheduled_date DATE NULL,
                completed_date DATE NULL,
                score INT NULL,
                notes TEXT NULL,
                created_by INT NULL,
                created_at DATETIME NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_audit_plans_policy
                    FOREIGN KEY (policy_id) REFERENCES audit_policies(id)
                    ON DELETE SET NULL,
                CONSTRAINT fk_audit_plans_auditor
                    FOREIGN KEY (auditor_id) REFERENCES users(id)
                    ON DELETE SET NULL,
                CONSTRAINT fk_audit_plans_department
                    FOREIGN KEY (department_id) REFERENCES departments(id)
                    ON DELETE SET NULL,
                CONSTRAINT fk_audit_plans_creator
                    FOREIGN KEY (created_by) REFERENCES users(id)
                    ON DELETE SET NULL
            )
        """))
        print("  Created audit_plans")
    else:
        print("  Exists audit_plans")

    if not inspector.has_table('audit_findings'):
        db.session.execute(text("""
            CREATE TABLE audit_findings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                audit_id INT NOT NULL,
                policy_id INT NULL,
                title VARCHAR(200) NOT NULL,
                severity VARCHAR(20) NOT NULL DEFAULT 'medium',
                status VARCHAR(30) NOT NULL DEFAULT 'open',
                owner_id INT NULL,
                description TEXT NULL,
                recommendation TEXT NULL,
                due_date DATE NULL,
                closed_at DATETIME NULL,
                created_at DATETIME NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_audit_findings_audit
                    FOREIGN KEY (audit_id) REFERENCES audit_plans(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_audit_findings_policy
                    FOREIGN KEY (policy_id) REFERENCES audit_policies(id)
                    ON DELETE SET NULL,
                CONSTRAINT fk_audit_findings_owner
                    FOREIGN KEY (owner_id) REFERENCES users(id)
                    ON DELETE SET NULL
            )
        """))
        print("  Created audit_findings")
    else:
        print("  Exists audit_findings")

    if not inspector.has_table('audit_corrective_actions'):
        db.session.execute(text("""
            CREATE TABLE audit_corrective_actions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                finding_id INT NOT NULL,
                title VARCHAR(200) NOT NULL,
                owner_id INT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'open',
                due_date DATE NULL,
                completed_at DATETIME NULL,
                notes TEXT NULL,
                created_at DATETIME NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_audit_actions_finding
                    FOREIGN KEY (finding_id) REFERENCES audit_findings(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_audit_actions_owner
                    FOREIGN KEY (owner_id) REFERENCES users(id)
                    ON DELETE SET NULL
            )
        """))
        print("  Created audit_corrective_actions")
    else:
        print("  Exists audit_corrective_actions")

    if not inspector.has_table('payroll_profiles'):
        db.session.execute(text("""
            CREATE TABLE payroll_profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                annual_ctc DECIMAL(12,2) NOT NULL DEFAULT 0,
                flexible_benefit_plan DECIMAL(12,2) NOT NULL DEFAULT 0,
                variable_pay DECIMAL(12,2) NOT NULL DEFAULT 0,
                basic_percent DECIMAL(5,2) NOT NULL DEFAULT 40,
                hra_percent DECIMAL(5,2) NOT NULL DEFAULT 20,
                tax_regime VARCHAR(20) NOT NULL DEFAULT 'new',
                pf_enabled TINYINT(1) NOT NULL DEFAULT 1,
                esi_enabled TINYINT(1) NOT NULL DEFAULT 0,
                pt_enabled TINYINT(1) NOT NULL DEFAULT 1,
                pf_number VARCHAR(30) NULL,
                uan_number VARCHAR(30) NULL,
                esi_number VARCHAR(30) NULL,
                eps_number VARCHAR(30) NULL,
                pan_number VARCHAR(20) NULL,
                bank_name VARCHAR(120) NULL,
                bank_account VARCHAR(40) NULL,
                ifsc_code VARCHAR(20) NULL,
                updated_by_id INT NULL,
                created_at DATETIME NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_payroll_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_payroll_profiles_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Created payroll_profiles")
    else:
        print("  Exists payroll_profiles")
        existing_payroll_columns = [c['name'] for c in inspector.get_columns('payroll_profiles')]
        payroll_profile_columns = [
            ("flexible_benefit_plan", "DECIMAL(12,2) NOT NULL DEFAULT 0"),
            ("variable_pay", "DECIMAL(12,2) NOT NULL DEFAULT 0"),
            ("pf_number", "VARCHAR(30) NULL"),
            ("eps_number", "VARCHAR(30) NULL"),
        ]
        for col_name, col_type in payroll_profile_columns:
            if col_name not in existing_payroll_columns:
                db.session.execute(text(f"ALTER TABLE payroll_profiles ADD COLUMN `{col_name}` {col_type}"))
                print(f"  Added payroll_profiles.{col_name}")
            else:
                print(f"  Exists payroll_profiles.{col_name}")

    if not inspector.has_table('statutory_components'):
        db.session.execute(text("""
            CREATE TABLE statutory_components (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(80) NOT NULL,
                component_type VARCHAR(30) NOT NULL DEFAULT 'deduction',
                code VARCHAR(30) NOT NULL UNIQUE,
                formula VARCHAR(255) NOT NULL,
                applies_to VARCHAR(80) NOT NULL DEFAULT 'all',
                is_active TINYINT(1) NOT NULL DEFAULT 1,
                created_by_id INT NULL,
                created_at DATETIME NULL,
                CONSTRAINT fk_statutory_components_creator FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Created statutory_components")
    else:
        print("  Exists statutory_components")
        try:
            db.session.execute(text("ALTER TABLE statutory_components MODIFY COLUMN component_type VARCHAR(30) NOT NULL DEFAULT 'deduction'"))
            print("  Updated statutory_components.component_type length")
        except Exception as exc:
            print(f"  Skipped statutory_components.component_type update: {exc}")

    if not inspector.has_table('investment_declarations'):
        db.session.execute(text("""
            CREATE TABLE investment_declarations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                financial_year VARCHAR(9) NOT NULL,
                section VARCHAR(40) NOT NULL DEFAULT '80C',
                description VARCHAR(180) NULL,
                declared_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                approved_amount DECIMAL(12,2) NULL,
                proof_filename VARCHAR(255) NULL,
                proof_original_name VARCHAR(255) NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'submitted',
                reviewer_id INT NULL,
                decision_note TEXT NULL,
                decided_at DATETIME NULL,
                created_at DATETIME NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_investment_declarations_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_investment_declarations_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Created investment_declarations")
    else:
        print("  Exists investment_declarations")

    if not inspector.has_table('loan_advances'):
        db.session.execute(text("""
            CREATE TABLE loan_advances (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                request_type VARCHAR(30) NOT NULL DEFAULT 'advance',
                amount DECIMAL(12,2) NOT NULL,
                repayment_months INT NOT NULL DEFAULT 1,
                purpose TEXT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                approver_id INT NULL,
                decision_note TEXT NULL,
                decided_at DATETIME NULL,
                disbursed_at DATETIME NULL,
                created_at DATETIME NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_loan_advances_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_loan_advances_approver FOREIGN KEY (approver_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Created loan_advances")
    else:
        print("  Exists loan_advances")

    if not inspector.has_table('biometric_logs'):
        db.session.execute(text("""
            CREATE TABLE biometric_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                employee_code VARCHAR(40) NOT NULL,
                user_id INT NULL,
                device_name VARCHAR(120) NULL,
                punch_time DATETIME NOT NULL,
                punch_type VARCHAR(20) NOT NULL DEFAULT 'in',
                sync_source VARCHAR(80) NOT NULL DEFAULT 'manual',
                synced_at DATETIME NULL,
                processed TINYINT(1) NOT NULL DEFAULT 0,
                CONSTRAINT fk_biometric_logs_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Created biometric_logs")
    else:
        print("  Exists biometric_logs")

    if not inspector.has_table('employee_profiles'):
        db.session.execute(text("""
            CREATE TABLE employee_profiles (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                date_of_birth DATE NULL,
                gender VARCHAR(30) NULL,
                marital_status VARCHAR(30) NULL,
                personal_email VARCHAR(120) NULL,
                blood_group VARCHAR(10) NULL,
                address_line1 VARCHAR(180) NULL,
                address_line2 VARCHAR(180) NULL,
                city VARCHAR(80) NULL,
                state VARCHAR(80) NULL,
                postal_code VARCHAR(20) NULL,
                country VARCHAR(80) NULL DEFAULT 'India',
                mobile_app_enabled TINYINT(1) NOT NULL DEFAULT 0,
                mobile_device_id VARCHAR(120) NULL,
                mobile_last_login DATETIME NULL,
                other_info TEXT NULL,
                updated_by_id INT NULL,
                created_at DATETIME NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_employee_profiles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_employee_profiles_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Created employee_profiles")
    else:
        print("  Exists employee_profiles")

    if not inspector.has_table('employee_documents'):
        db.session.execute(text("""
            CREATE TABLE employee_documents (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                document_type VARCHAR(60) NOT NULL DEFAULT 'certificate',
                title VARCHAR(160) NOT NULL,
                stored_filename VARCHAR(255) NOT NULL,
                original_filename VARCHAR(255) NOT NULL,
                mimetype VARCHAR(120) NULL,
                file_size INT NULL,
                notes TEXT NULL,
                uploaded_by_id INT NULL,
                created_at DATETIME NULL,
                CONSTRAINT fk_employee_documents_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_employee_documents_uploader FOREIGN KEY (uploaded_by_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Created employee_documents")
    else:
        print("  Exists employee_documents")

    if not inspector.has_table('employee_salary_history'):
        db.session.execute(text("""
            CREATE TABLE employee_salary_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                annual_ctc DECIMAL(12,2) NOT NULL DEFAULT 0,
                flexible_benefit_plan DECIMAL(12,2) NOT NULL DEFAULT 0,
                variable_pay DECIMAL(12,2) NOT NULL DEFAULT 0,
                effective_from DATE NOT NULL,
                change_reason VARCHAR(180) NULL,
                created_by_id INT NULL,
                created_at DATETIME NULL,
                CONSTRAINT fk_employee_salary_history_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_employee_salary_history_creator FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Created employee_salary_history")
    else:
        print("  Exists employee_salary_history")

    if not inspector.has_table('employee_salary_components'):
        db.session.execute(text("""
            CREATE TABLE employee_salary_components (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                name VARCHAR(120) NOT NULL,
                amount DECIMAL(12,2) NOT NULL DEFAULT 0,
                component_group VARCHAR(30) NOT NULL DEFAULT 'ctc',
                is_fbp TINYINT(1) NOT NULL DEFAULT 0,
                sort_order INT NOT NULL DEFAULT 0,
                updated_by_id INT NULL,
                created_at DATETIME NULL,
                updated_at DATETIME NULL,
                CONSTRAINT fk_employee_salary_components_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                CONSTRAINT fk_employee_salary_components_updated_by FOREIGN KEY (updated_by_id) REFERENCES users(id) ON DELETE SET NULL
            )
        """))
        print("  Created employee_salary_components")
    else:
        print("  Exists employee_salary_components")

    default_components = [
        ("Employee Provident Fund", "deduction", "PF_EMPLOYEE", "basic * 0.12", "pf_enabled"),
        ("Employer Provident Fund", "employer", "PF_EMPLOYER", "basic * 0.12", "pf_enabled"),
        ("ESIC Employee", "deduction", "ESIC_EMPLOYEE", "gross * 0.0075", "esi_enabled"),
        ("ESIC Employer", "employer", "ESIC_EMPLOYER", "gross * 0.0325", "esi_enabled"),
        ("Professional Tax", "deduction", "PT", "state_slab(monthly_gross)", "pt_enabled"),
    ]
    if inspector.has_table('statutory_components'):
        for name, component_type, code, formula, applies_to in default_components:
            db.session.execute(text("""
                INSERT INTO statutory_components
                    (name, component_type, code, formula, applies_to, is_active, created_at)
                SELECT :name, :component_type, :code, :formula, :applies_to, 1, NOW()
                WHERE NOT EXISTS (
                    SELECT 1 FROM statutory_components WHERE code = :code
                )
            """), {
                "name": name,
                "component_type": component_type,
                "code": code,
                "formula": formula,
                "applies_to": applies_to,
            })
        print("  Default statutory components ready")

    db.session.commit()
    print("\nAll columns ready!")
