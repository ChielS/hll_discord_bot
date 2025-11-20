"""Test script to generate sample servers YAML."""
import yaml
from database.db import Database


def generate_servers_yaml():
    """Generate sample servers YAML file."""
    db = Database()

    # Get all servers
    servers = db.get_all_servers()

    # Create YAML data
    yaml_data = {
        "total_servers": len(servers),
        "instructions": "Edit the 'status' field for any server (active/skip), then upload this file using /update_servers",
        "status_options": ["active", "skip"],
        "servers": []
    }

    for server in servers:
        server_data = {
            "name": server['name'],
            "url": server['url'],
            "description": server['description'],
            "status": server['status'],
            "clan": server['clan']
        }
        yaml_data['servers'].append(server_data)

    # Save to file
    filename = "sample_servers.yaml"
    with open(filename, 'w', encoding='utf-8') as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"✅ Generated {filename}")
    print(f"🖥️ Contains {len(servers)} servers")

    # Count by status
    active = sum(1 for s in servers if s['status'] == 'active')
    skip = sum(1 for s in servers if s['status'] == 'skip')

    print(f"\nStatus breakdown:")
    print(f"  - Active: {active}")
    print(f"  - Skip: {skip}")

    # Show first 5 servers
    print("\nFirst 5 servers:")
    print("-" * 80)
    for server in servers[:5]:
        print(f"{server['name']:<20} | {server['status']:<10} | {server['description']}")


def main():
    """Generate sample servers YAML."""
    generate_servers_yaml()


if __name__ == "__main__":
    main()
