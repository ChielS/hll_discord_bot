"""Script to load servers from servers.yaml into the database."""
import yaml
from database.db import Database


def load_servers_from_yaml(yaml_file: str = "servers.yaml"):
    """Load servers from YAML file into the database.

    Args:
        yaml_file: Path to the YAML file containing server data
    """
    # Initialize database
    db = Database()

    # Read YAML file
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)

    # Get servers list
    servers = data.get('servers', [])

    if not servers:
        print("No servers found in YAML file.")
        return

    # Add each server to database
    added_count = 0
    for server in servers:
        name = server.get('name')
        url = server.get('url')
        description = server.get('description')
        status = server.get('status')
        clan = server.get('clan')

        # Validate required fields
        if not all([name, url, description, status, clan]):
            print(f"Skipping server with missing fields: {server}")
            continue

        try:
            db.add_server(name, url, description, status, clan)
            print(f"Added server: {name} ({description})")
            added_count += 1
        except Exception as e:
            print(f"Error adding server {name}: {e}")

    print(f"\nSuccessfully loaded {added_count} servers into the database.")

    # Display summary
    all_servers = db.get_all_servers()
    active_servers = [s for s in all_servers if s['status'] == 'active']
    skip_servers = [s for s in all_servers if s['status'] == 'skip']

    print(f"\nDatabase Summary:")
    print(f"  Total servers: {len(all_servers)}")
    print(f"  Active servers: {len(active_servers)}")
    print(f"  Skip servers: {len(skip_servers)}")


if __name__ == "__main__":
    load_servers_from_yaml()
