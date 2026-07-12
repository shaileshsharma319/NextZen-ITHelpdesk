"""
Seed workstation assets from the hostname/IP/user mapping.
Usage: python seed_assets.py
"""
from app import create_app, db
from app.models.asset import Asset
from app.models.user import User

app = create_app()

# (hostname_raw, ip, user_full_name)
# Brand/model hints extracted from hostname notes in parentheses
ASSETS = [
    ("winsoft-8",                                    "192.91.201.8",   "Sudesh Ingole"),
    ("Winsoft-9",                                    "192.91.201.9",   "Ali Hasan Khan"),
    ("Winsoft-10",                                   "192.91.201.10",  "Om Patil"),
    ("Winsoft-15",                                   "192.91.201.15",  "Secondary Domain"),
    ("Winsoft-17",                                   "192.91.201.17",  "Suyog Zambare"),
    ("Winsoft-18",                                   "192.91.201.18",  "Jay Dalal"),
    ("Winsoft-19",                                   "192.91.201.19",  "Akshay Shah"),
    ("winsoft-20",                                   "192.91.201.20",  "Ashutosh Dubey"),
    ("winsoft-21",                                   "192.91.201.21",  "Rakesh Kumar Dash"),
    ("Winsoft-22",                                   "192.91.201.22",  "Pratik Jadhav"),
    ("Winsoft-23",                                   "192.91.201.23",  "Yash Dhapodkar"),
    ("Winsoft-26",                                   "192.91.201.26",  "Nikhil Sarde"),
    ("Winsoft-29",                                   "192.91.201.183", "Raj Kumar"),
    ("winsoft-30",                                   "192.91.201.30",  "Shailesh Sharma"),
    ("Winsoft-32",                                   "192.91.201.32",  "Shiv Shankar Pandit"),
    ("Winsoft-39",                                   "192.91.201.39",  "Ajay Sonawale"),
    ("Winsoft-41 (VM on winsoft-205)",               "192.91.201.41",  "Soumitra Sir IIS VM"),
    ("winsoft-44",                                   "192.91.201.44",  "Shreyas Jadhav"),
    ("Winsoft-45",                                   "192.91.201.45",  "App Support"),
    ("winsoft-46",                                   "192.91.201.46",  "Pradeep Sawant"),
    ("Winsoft-47",                                   "192.91.201.47",  "Rounak Ghosh"),
    ("Winsoft-49",                                   "192.91.201.49",  "Sahili Choure"),
    ("winsoft-54",                                   "192.91.201.54",  "Pratham Jogi"),
    ("Winsoft-60",                                   "192.91.201.60",  "Shobhnath Yadav"),
    ("Winsoft-61",                                   "192.91.201.61",  "Siddharth Singh"),
    ("Winsoft-64",                                   "192.91.201.64",  "Mohit Patil"),
    ("winsoft-65",                                   "192.91.201.65",  "Amit Singh"),
    ("Winsoft-68",                                   "192.91.201.68",  "Hemangi Khot"),
    ("Winsoft-70 (Lenovo Laptop)",                   "192.91.201.70",  "Ankur Kadam"),
    ("winsoft-72",                                   "192.91.201.72",  "Onkar Mhaske"),
    ("winsoft-73 (HP 14s Intel Core i3 11th)",       "192.91.201.73",  "Riya Thakkar"),
    ("Winsoft-74 (HP 14s Intel Core i3 11th)",       "192.91.201.74",  "Rushikesh Patil"),
    ("Winsoft-75 (HP 14s Intel Core i3 11th)",       "192.91.201.75",  "Soham Pathak"),
    ("Winsoft-76 (HP 14s Intel Core i3 11th)",       "192.91.201.76",  "Sanket Mahadik"),
    ("winsoft-78",                                   "192.91.201.78",  "Aryan Garate"),
    ("Winsoft-79 (HP 14s Intel Core i3 11th)",       "192.91.201.79",  "Laxmi Shinde"),
    ("Winsoft-81",                                   "192.91.201.81",  "Pranita Pawar"),
    ("winsoft-83 (HP)",                              "192.91.201.83",  "Pranay Kamble"),
    ("winsoft-85 (Lenovo)",                          "192.91.201.85",  "Anand Sharma"),
    ("winsoft-86",                                   "192.91.201.86",  "Vaishnavi Mhaske"),
    ("Winsoft-88",                                   "192.91.201.88",  "Shubham Ghule"),
    ("Winsoft-89",                                   "192.91.201.89",  "Narayan Kale"),
    ("Winsoft-90",                                   "192.91.201.90",  "Prakash Choure"),
    ("Winsoft-92",                                   "192.91.201.92",  "Sneha Sonawane"),
    ("Winsoft-93",                                   "192.91.201.93",  "Shubham Kumawat"),
    ("Winsoft-95",                                   "192.91.201.95",  "Saiteja Adepu"),
    ("Winsoft-96",                                   "192.91.201.96",  "Sanket Mulay"),
    ("Winsoft-97",                                   "192.91.201.97",  "Teja Borapureddi"),
    ("Winsoft-103",                                  "192.91.201.103", "Tanish Thomabre"),
    ("Winsoft-104",                                  "192.91.201.104", "Supriya Malbari"),
    ("Winsoft-107 (HP new)",                         "192.91.201.107", "Sayali Bhandari"),
    ("Winsoft-112",                                  "192.91.201.112", "Sanvi Patil"),
    ("Winsoft-124",                                  "192.91.201.124", "Ankita Angne"),
    ("winsoft-171 (Dell Laptop Vostro 3401)",        "192.91.201.171", "Ashish Gupta"),
    ("winsoft-172 (Dell Laptop Vostro 3401)",        "192.91.201.172", "Rushang Thakkar"),
    ("winsoft-173 (AVITA Essential NE14A2)",         "192.91.201.173", "Shiv Shankar Pandit 2"),
    ("winsoft-211 (Dell Vostro 3500)",               "192.91.201.211", "Param Uni"),
    ("winsoft-212 (Dell Vostro 3500)",               "192.91.201.212", "Apeksha Patil"),
    ("winsoft-213",                                  "192.91.201.213", "Jay Phad"),
    ("Winsoft-214 (Lenovo V15)",                     "192.91.201.214", "Trupti Tilwe"),
    ("Winsoft-215 (Lenovo V15)",                     "192.91.201.215", "Soumitra Chatterjee"),
    ("Winsoft-216 (Lenovo V15)",                     "192.91.201.216", "Rajesh Jadhav"),
    ("Winsoft-217 (Lenovo V15)",                     "192.91.201.217", "Kishor Shirsath"),
    ("Winsoft-218 (Lenovo V15)",                     "192.91.201.218", "Vandana Chinchavale"),
    ("Winsoft-219 (HP 14s)",                         "192.91.201.219", "Tulika Kanaujia"),
    ("Winsoft-220 (Lenovo V15)",                     "192.91.201.220", "Tanaya Kumbharkar"),
    ("Winsoft-221 (Lenovo V15)",                     "192.91.201.221", "Dhanashree Pednekar"),
    ("winsoft-225 (Lenovo V15 G2 IRL)",              "192.91.201.225", "Srinivas Alwala"),
    ("winsoft-226 (Lenovo V15 IIL)",                 "192.91.201.226", "Poonam Hinge"),
    ("Winsoft-233 (VM on winsoft-206)",              "192.91.201.233", "Govind Sir"),
]


def parse_brand_model(hostname_raw):
    """Extract brand and model hints from hostname notes."""
    notes = hostname_raw.lower()
    brand, model = None, None
    if "lenovo" in notes:
        brand = "Lenovo"
        if "v15 g2" in notes:        model = "V15 G2 IRL"
        elif "v15 iil" in notes:     model = "V15 IIL"
        elif "v15" in notes:         model = "V15"
        elif "laptop" in notes:      model = "Laptop"
    elif "hp" in notes:
        brand = "HP"
        if "14s" in notes:           model = "14s Intel Core i3 11th Gen"
        elif "new" in notes:         model = "14s (New)"
        else:                        model = "HP Laptop"
    elif "dell" in notes:
        brand = "Dell"
        if "vostro 3401" in notes:   model = "Vostro 3401"
        elif "vostro 3500" in notes: model = "Vostro 3500"
        else:                        model = "Vostro"
    elif "avita" in notes:
        brand = "AVITA"
        model = "Essential NE14A2"
    return brand, model


def clean_hostname(raw):
    """Extract just the hostname part before any parenthesis."""
    return raw.split("(")[0].strip().lower()


def is_vm(raw):
    return "vm" in raw.lower()


with app.app_context():
    # Build name -> user_id lookup (case-insensitive)
    all_users = User.query.all()
    name_map = {u.name.lower().strip(): u.id for u in all_users}

    existing_tags = {a.asset_tag for a in Asset.query.all()}

    created, skipped, unmatched = [], [], []

    for hostname_raw, ip, user_name in ASSETS:
        hostname   = clean_hostname(hostname_raw)
        asset_tag  = hostname.upper().replace(" ", "")

        # Skip if already exists
        if asset_tag in existing_tags:
            skipped.append(asset_tag)
            continue

        # Resolve user
        user_id = name_map.get(user_name.lower().strip())
        if not user_id:
            # Try partial match on first word of name
            first_word = user_name.lower().split()[0]
            user_id = next((uid for uname, uid in name_map.items() if uname.startswith(first_word)), None)
        if not user_id:
            unmatched.append((asset_tag, user_name))

        brand, model = parse_brand_model(hostname_raw)
        asset_type   = "server" if is_vm(hostname_raw) else "computer"
        status       = "in_use" if user_id else "available"

        a = Asset(
            name             = hostname_raw.split("(")[0].strip(),
            asset_tag        = asset_tag,
            asset_type       = asset_type,
            hostname         = hostname,
            ip_address       = ip,
            status           = status,
            brand            = brand,
            model            = model,
            assigned_user_id = user_id,
            remarks          = hostname_raw if "(" in hostname_raw else None,
        )
        db.session.add(a)
        existing_tags.add(asset_tag)
        created.append((asset_tag, hostname_raw.split("(")[0].strip(), ip, user_name, "matched" if user_id else "NO USER"))

    db.session.commit()

    print(f"\n{'Asset Tag':<20} {'Hostname':<22} {'IP':<18} {'Assigned To':<28} {'Status'}")
    print("-" * 100)
    for tag, name, ip, user, status in created:
        print(f"{tag:<20} {name:<22} {ip:<18} {user:<28} {status}")

    print(f"\nCreated : {len(created)}")
    print(f"Skipped : {len(skipped)} (already exist)")
    if unmatched:
        print(f"\nUnmatched users ({len(unmatched)}):")
        for tag, uname in unmatched:
            print(f"  {tag} -> '{uname}'")
