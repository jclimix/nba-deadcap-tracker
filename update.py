import re
from datetime import datetime

def get_current_version():
    """Reads the current version from version.txt."""
    try:
        with open("version.txt", "r") as f:
            version = f.read().strip()
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            raise ValueError("Invalid version format in version.txt.")
        return version
    except FileNotFoundError:
        print("version.txt not found. Creating a new one with version 0.1.0.")
        return "0.1.0"
    except ValueError as e:
        print(e)
        return None

def increment_version(version, bump_type):
    """Increments the version based on the bump type: major, minor, or patch."""
    major, minor, patch = map(int, version.split("."))
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        print("Invalid bump type. Using patch as default.")
        patch += 1
    return f"{major}.{minor}.{patch}"

def get_bump_type():
    """Prompts the user to choose a version bump type."""
    print("\nChoose the version bump type:")
    print("1. Major")
    print("2. Minor")
    print("3. Patch (default)")
    choice = input("Enter 1, 2, or 3: ").strip()
    if choice == "1":
        return "major"
    elif choice == "2":
        return "minor"
    elif choice == "3":
        return "patch"
    else:
        print("Invalid choice. Defaulting to patch.")
        return "patch"

def update_version_file(new_version):
    """Writes the new version to version.txt."""
    with open("version.txt", "w") as f:
        f.write(new_version)

def update_changelog(new_version, changes):
    """Updates the CHANGELOG.md file with the new version and changes."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    changelog_entry = f"## [{new_version}] - {date_str}\n"
    for change in changes:
        changelog_entry += f"- {change}\n"
    changelog_entry += "\n"

    try:
        with open("CHANGELOG.md", "r") as f:
            content = f.read()
            
        if "# Changelog" in content:

            parts = content.split("# Changelog", 1)
            header = parts[0] + "# Changelog"
            rest = parts[1]
            updated_content = header + "\n\n" + changelog_entry + rest.lstrip()
        else:

            updated_content = "# Changelog\n\n" + changelog_entry + content
            
        with open("CHANGELOG.md", "w") as f:
            f.write(updated_content)
            
    except FileNotFoundError:
        with open("CHANGELOG.md", "w") as f:
            f.write("# Changelog\n\n")
            f.write(changelog_entry)

def main():
    current_version = get_current_version()
    if not current_version:
        return

    bump_type = get_bump_type()
    new_version = increment_version(current_version, bump_type)
    print(f"\nCurrent version: {current_version}")
    print(f"New version: {new_version}")

    print("\nEnter the list of changes for this version (hit Enter on an empty line to finish):")
    changes = []
    while True:
        change = input("- ")
        if not change.strip():
            break
        changes.append(change)

    if changes:
        update_version_file(new_version)
        update_changelog(new_version, changes)
        print(f"\nversion.txt updated to {new_version}")
        print("CHANGELOG.md updated successfully.")
    else:
        print("No changes provided. Aborting update.")

if __name__ == "__main__":
    main()