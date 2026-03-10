#!/usr/bin/env python3
"""Quick proxy configuration helper.

This script helps you quickly configure your proxy settings.

Usage:
    uv run python examples/quick_proxy_setup.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def interactive_proxy_setup() -> None:
    """Interactive proxy configuration setup."""
    print("\n" + "="*80)
    print("🔧 Polymarket Trader - Proxy Configuration Helper")
    print("="*80 + "\n")

    print("This script will help you configure your proxy settings for web search.\n")

    # Common proxy presets
    print("📋 Common proxy configurations:")
    print("  1. Clash          http://127.0.0.1:7890")
    print("  2. V2Ray          http://127.0.0.1:10809")
    print("  3. Shadowsocks    http://127.0.0.1:1087")
    print("  4. Custom        Enter your own")
    print("  5. No proxy      Disable web search\n")

    choice = input("Select option (1-5): ").strip()

    proxy_urls = {
        "1": "http://127.0.0.1:7890",
        "2": "http://127.0.0.1:10809",
        "3": "http://127.0.0.1:1087",
        "4": None,
        "5": "DISABLE",
    }

    proxy_url = proxy_urls.get(choice)

    if choice == "4":
        proxy_url = input("Enter your proxy URL (e.g., http://127.0.0.1:1087): ").strip()
        if not proxy_url:
            print("❌ Invalid proxy URL")
            return

    if proxy_url == "DISABLE":
        print("\n⚠️  Web search will be disabled")
        confirm = input("Continue? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled")
            return
        proxy_url = None

    # Show configuration
    print(f"\n📝 Configuration Summary:")
    print(f"  Proxy URL: {proxy_url if proxy_url else 'Disabled'}")
    print(f"  Enabled: {'Yes' if proxy_url else 'No'}")

    if proxy_url:
        print(f"\n💡 The following lines will be added to your .env file:")
        print(f"  WEB_RESEARCH_ENABLED=true")
        print(f"  WEB_RESEARCH_PROXY_URL={proxy_url}")
        print(f"  WEB_RESEARCH_SEARCH_ENGINE=google")
        print(f"  WEB_RESEARCH_MAX_RESULTS=10")
        print(f"  WEB_RESEARCH_TIMEOUT_SECONDS=30")

    confirm = input(f"\nApply this configuration? (y/n): ").strip().lower()

    if confirm != "y":
        print("Cancelled")
        return

    # Update .env file
    env_path = project_root / ".env"

    if not env_path.exists():
        print(f"\n❌ .env file not found at {env_path}")
        print("💡 Create a .env file first (copy from .env.example)")
        return

    try:
        with open(env_path, "r") as f:
            env_content = f.read()

        # Remove existing WEB_RESEARCH_ lines
        lines = []
        for line in env_content.split("\n"):
            if not line.startswith("WEB_RESEARCH_"):
                lines.append(line)

        # Add new configuration
        if proxy_url:
            lines.extend([
                "",
                "# Web Research Configuration",
                "WEB_RESEARCH_ENABLED=true",
                f"WEB_RESEARCH_PROXY_URL={proxy_url}",
                "WEB_RESEARCH_SEARCH_ENGINE=google",
                "WEB_RESEARCH_MAX_RESULTS=10",
                "WEB_RESEARCH_TIMEOUT_SECONDS=30",
            ])
        else:
            lines.extend([
                "",
                "# Web Research Configuration (Disabled)",
                "WEB_RESEARCH_ENABLED=false",
            ])

        # Write back
        with open(env_path, "w") as f:
            f.write("\n".join(lines))

        print(f"\n✅ Configuration updated successfully!")
        print(f"   File: {env_path}")

        if proxy_url:
            print(f"\n🧪 Test your configuration:")
            print(f"   uv run python examples/test_proxy_connection.py")
        else:
            print(f"\n⚠️  Web search has been disabled")

    except Exception as e:
        print(f"\n❌ Error updating .env file: {e}")
        return


def show_current_config() -> None:
    """Show current proxy configuration."""
    from src.config import settings

    print("\n" + "="*80)
    print("📋 Current Proxy Configuration")
    print("="*80 + "\n")

    print("Web Research Settings:")
    print(f"  Enabled: {settings.web_research.enabled}")
    print(f"  Proxy URL: {settings.web_research.proxy_url if settings.web_research.proxy_url else 'Not configured'}")
    print(f"  Search Engine: {settings.web_research.search_engine}")
    print(f"  Max Results: {settings.web_research.max_results}")
    print(f"  Timeout: {settings.web_research.timeout_seconds}s")

    if settings.web_research.proxy_url:
        print(f"\n✅ Proxy is configured")
        print(f"💡 Test connection: uv run python examples/test_proxy_connection.py")
    else:
        print(f"\n⚠️  Proxy not configured")
        print(f"💡 Run this script again to configure: uv run python examples/quick_proxy_setup.py")

    print()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Quick proxy configuration helper"
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Show current configuration"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run interactive setup"
    )

    args = parser.parse_args()

    if args.show:
        show_current_config()
    elif args.setup:
        interactive_proxy_setup()
    else:
        # Default: show current config, then offer setup
        show_current_config()

        from src.config import settings

        if not settings.web_research.proxy_url and settings.web_research.enabled:
            print("🔧 Would you like to configure your proxy now? (y/n): ", end="")
            if input().strip().lower() == "y":
                interactive_proxy_setup()


if __name__ == "__main__":
    main()
