import pkgutil
import subprocess

# List of all modules being used
modules = [
    'flask', 'flask_babel', 'flask_login', 'flask_mail', 'flask_paranoid',
    'flask_principal', 'flask_security', 'flask_socketio', 'flask_wtf',
    'pyotp', 'qrcode', 'twilio', 'dateutil', 'jsonformatter', 'psycopg2',
    'werkzeug', 'passlib', 'pkg_resources'
]

# List missing modules
missing_modules = [mod for mod in modules if pkgutil.find_loader(mod) is None]

# Save missing modules to a file
if missing_modules:
    print("\nMissing Modules Found:")
    with open("requirements_missing.txt", "w") as f:
        for mod in missing_modules:
            print(f"- {mod}")
            f.write(f"{mod}\n")

    print("\n✅ Missing modules saved to 'requirements_missing.txt'")
else:
    print("\n🎯 No missing modules found!")
