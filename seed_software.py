"""
Seed software list.
Usage: python seed_software.py
"""
from app import create_app, db
from app.models.software import Software

app = create_app()

# (name, version, vendor, category, license_type)
SOFTWARE = [
    # ── Reporting ──
    ("Crystal Reports",             "9",                "SAP",              "other",        "commercial"),
    ("Crystal Reports",             "2008",             "SAP",              "other",        "commercial"),
    ("Crystal Reports",             "2013",             "SAP",              "other",        "commercial"),
    ("Crystal Reports",             "10",               "SAP",              "other",        "commercial"),

    # ── OS ──
    ("Windows 7 Professional x86",  "x86",              "Microsoft",        "os",           "commercial"),
    ("Windows 7 Professional x64",  "x64",              "Microsoft",        "os",           "commercial"),
    ("Windows 8",                   "8",                "Microsoft",        "os",           "commercial"),
    ("Windows 10",                  "10",               "Microsoft",        "os",           "commercial"),
    ("Windows 11",                  "11",               "Microsoft",        "os",           "commercial"),
    ("Windows Server 2008 Enterprise", "2008",          "Microsoft",        "os",           "commercial"),
    ("Windows Server 2008 Standard",   "2008",          "Microsoft",        "os",           "commercial"),
    ("Windows Server 2012 R2 Standard","2012 R2",       "Microsoft",        "os",           "commercial"),
    ("Windows Server 2016 Standard",   "2016",          "Microsoft",        "os",           "commercial"),
    ("Windows Server 2022 Standard Evaluation", "2022", "Microsoft",        "os",           "trial"),
    ("Ubuntu OS",                   "22.04 LTS",        "Canonical",        "os",           "open_source"),
    ("CentOS",                      "",                 "Red Hat",          "os",           "open_source"),
    ("FreeBSD",                     "",                 "FreeBSD Project",  "os",           "open_source"),

    # ── Office / Productivity ──
    ("Microsoft Office",            "2010 Standard",    "Microsoft",        "office",       "commercial"),
    ("Microsoft Office",            "2013 Standard",    "Microsoft",        "office",       "commercial"),
    ("Microsoft Office",            "2016",             "Microsoft",        "office",       "commercial"),
    ("Microsoft Office 365",        "365",              "Microsoft",        "office",       "subscription"),
    ("MS Project",                  "2013 Professional","Microsoft",        "office",       "commercial"),
    ("MS Visio",                    "2013 Professional","Microsoft",        "office",       "commercial"),
    ("Kingsoft Office",             "",                 "Kingsoft",         "office",       "commercial"),
    ("Tally Prime",                 "",                 "Tally Solutions",  "office",       "commercial"),
    ("Tally Graph",                 "",                 "Tally Solutions",  "office",       "commercial"),

    # ── Development ──
    ("MS Visual Studio",            "2013 Professional","Microsoft",        "development",  "commercial"),
    ("MS Visual Studio",            "2017 Professional","Microsoft",        "development",  "commercial"),
    ("MS Visual Studio",            "2019 Professional","Microsoft",        "development",  "commercial"),
    ("MS Visual Studio",            "2022 Professional Trial", "Microsoft", "development",  "trial"),
    ("MS Visual Studio",            "2026 Professional Trial", "Microsoft", "development",  "trial"),
    ("Infragistics NetAdvantage",   "2004",             "Infragistics",     "development",  "commercial"),
    ("Infragistics NetAdvantage",   "2005",             "Infragistics",     "development",  "commercial"),
    ("Oracle Database Client",      "9i",               "Oracle",           "development",  "commercial"),
    ("Oracle Database Server",      "9i",               "Oracle",           "development",  "commercial"),
    ("Oracle Database Client",      "11g",              "Oracle",           "development",  "commercial"),
    ("Oracle Database Server",      "11g",              "Oracle",           "development",  "commercial"),
    ("Oracle Database Client",      "12c",              "Oracle",           "development",  "commercial"),
    ("Oracle Database Server",      "12c",              "Oracle",           "development",  "commercial"),
    ("Oracle Database Client",      "19c",              "Oracle",           "development",  "commercial"),
    ("Oracle Database Server",      "19c",              "Oracle",           "development",  "commercial"),
    ("SQL Server Express",          "2005",             "Microsoft",        "development",  "free"),
    ("SQL Server Express",          "2008",             "Microsoft",        "development",  "free"),
    ("SQL Server R2 Standard",      "2008 R2",          "Microsoft",        "development",  "commercial"),
    ("SQL Server R2 Standard Client","2008 R2",         "Microsoft",        "development",  "commercial"),
    ("SQL Server Developer",        "2014",             "Microsoft",        "development",  "commercial"),
    ("SQL Server Developer",        "2016",             "Microsoft",        "development",  "commercial"),
    ("SQL Server Developer",        "2017 Client",      "Microsoft",        "development",  "commercial"),
    ("SQL Server Developer",        "2019 Client",      "Microsoft",        "development",  "commercial"),
    ("SQL Server Developer",        "2019",             "Microsoft",        "development",  "commercial"),
    ("SQL Server Developer",        "2022",             "Microsoft",        "development",  "commercial"),
    ("SQL Server Developer",        "2025",             "Microsoft",        "development",  "commercial"),
    ("SourceSafe Client",           "2005",             "Microsoft",        "development",  "commercial"),
    ("SVN CollabNet SubversionEdge","",                 "CollabNet",        "development",  "open_source"),
    ("WAMP Server",                 "",                 "WampServer",       "development",  "free"),
    ("SoapUI",                      "",                 "SmartBear",        "development",  "free"),
    ("Beyond Compare",              "",                 "Scooter Software", "development",  "commercial"),
    ("DBF View",                    "Trial",            "DBFView",          "development",  "trial"),
    ("Burp Suite",                  "",                 "PortSwigger",      "security",     "free"),

    # ── Security ──
    ("Kaspersky Client",            "",                 "Kaspersky",        "security",     "commercial"),

    # ── Utility ──
    ("TightVNC",                    "",                 "TightVNC",         "utility",      "free"),
    ("Foxit Phantom PDF",           "",                 "Foxit",            "utility",      "commercial"),
    ("GST Offline Tool",            "",                 "GSTN",             "utility",      "free"),
    ("eTDS Wizard",                 "",                 "EaseProcess",      "utility",      "commercial"),
]


with app.app_context():
    existing = {(s.name, s.version) for s in Software.query.all()}
    created = 0

    for name, version, vendor, category, license_type in SOFTWARE:
        if (name, version) in existing:
            print(f"  Skip: {name} {version}")
            continue
        sw = Software(
            name         = name,
            version      = version or None,
            vendor       = vendor,
            category     = category,
            license_type = license_type,
        )
        db.session.add(sw)
        existing.add((name, version))
        created += 1

    db.session.commit()

    print(f"\n{'#':<5} {'Name':<40} {'Version':<28} {'Category':<14} {'License'}")
    print("-" * 105)
    for i, (name, version, vendor, category, license_type) in enumerate(SOFTWARE, 1):
        print(f"{i:<5} {name:<40} {version:<28} {category:<14} {license_type}")

    print(f"\nCreated: {created}  |  Total in DB: {Software.query.count()}")
