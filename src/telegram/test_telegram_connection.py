"""
Telegram Connection Test
Diagnoses network connectivity issues with Telegram API
"""

import os
import sys
import asyncio
import httpx
from colorama import init, Fore, Style
from dotenv import load_dotenv

init(autoreset=True)
load_dotenv()

def print_header(text):
    print("\n" + "=" * 80)
    print(Fore.CYAN + Style.BRIGHT + text)
    print("=" * 80)

async def test_internet_connection():
    """Test basic internet connectivity"""
    print_header("TEST 1: BASIC INTERNET CONNECTIVITY")
    
    test_urls = [
        "https://www.google.com",
        "https://www.cloudflare.com",
        "https://api.ipify.org"
    ]
    
    for url in test_urls:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    print(f"{Fore.GREEN}[OK] {url} - Reachable")
                else:
                    print(f"{Fore.YELLOW}[WARNING] {url} - Status {response.status_code}")
        except Exception as e:
            print(f"{Fore.RED}[FAIL] {url} - {e}")
            return False
    
    return True

async def test_telegram_api():
    """Test Telegram API connectivity"""
    print_header("TEST 2: TELEGRAM API CONNECTIVITY")
    
    telegram_urls = [
        "https://api.telegram.org",
        "https://core.telegram.org"
    ]
    
    for url in telegram_urls:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url)
                print(f"{Fore.GREEN}[OK] {url} - Reachable (Status: {response.status_code})")
        except httpx.ConnectTimeout:
            print(f"{Fore.RED}[FAIL] {url} - Connection Timeout")
            print(Fore.YELLOW + "  This indicates Telegram API is being blocked")
            return False
        except httpx.ConnectError:
            print(f"{Fore.RED}[FAIL] {url} - Connection Error")
            print(Fore.YELLOW + "  Cannot reach Telegram servers")
            return False
        except Exception as e:
            print(f"{Fore.RED}[FAIL] {url} - {e}")
            return False
    
    return True

async def test_bot_token():
    """Test bot token validity"""
    print_header("TEST 3: BOT TOKEN VALIDATION")
    
    token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    if not token:
        print(f"{Fore.RED}[FAIL] No TELEGRAM_BOT_TOKEN found in .env file")
        return False
    
    print(f"Token format: {token[:10]}...{token[-10:]}")
    
    # Check token format
    if ':' not in token:
        print(f"{Fore.RED}[FAIL] Invalid token format (should contain ':')")
        return False
    
    parts = token.split(':')
    if len(parts) != 2:
        print(f"{Fore.RED}[FAIL] Invalid token format (should be BOT_ID:TOKEN)")
        return False
    
    try:
        bot_id = int(parts[0])
        print(f"{Fore.GREEN}[OK] Bot ID: {bot_id}")
    except ValueError:
        print(f"{Fore.RED}[FAIL] Invalid bot ID (should be numeric)")
        return False
    
    # Test with Telegram API
    print("\nTesting token with Telegram API...")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"https://api.telegram.org/bot{token}/getMe"
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    bot_info = data.get('result', {})
                    print(f"{Fore.GREEN}[OK] Bot token is VALID")
                    print(f"  Bot Name: {bot_info.get('first_name', 'N/A')}")
                    print(f"  Username: @{bot_info.get('username', 'N/A')}")
                    print(f"  Bot ID: {bot_info.get('id', 'N/A')}")
                    return True
                else:
                    print(f"{Fore.RED}[FAIL] API returned error: {data}")
                    return False
            else:
                print(f"{Fore.RED}[FAIL] HTTP Status: {response.status_code}")
                print(f"  Response: {response.text}")
                return False
                
    except httpx.ConnectTimeout:
        print(f"{Fore.RED}[FAIL] Connection timeout - Telegram API blocked or slow network")
        return False
    except Exception as e:
        print(f"{Fore.RED}[FAIL] Error: {e}")
        return False

async def test_dns_resolution():
    """Test DNS resolution for Telegram"""
    print_header("TEST 4: DNS RESOLUTION")
    
    import socket
    
    domains = [
        "api.telegram.org",
        "core.telegram.org"
    ]
    
    for domain in domains:
        try:
            ip = socket.gethostbyname(domain)
            print(f"{Fore.GREEN}[OK] {domain} -> {ip}")
        except Exception as e:
            print(f"{Fore.RED}[FAIL] {domain} - {e}")
            return False
    
    return True

async def test_firewall():
    """Check for firewall issues"""
    print_header("TEST 5: FIREWALL CHECK")
    
    print("Checking if firewall might be blocking Telegram...")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try different Telegram IPs
            response = await client.get("https://149.154.167.220")  # Telegram server IP
            print(f"{Fore.GREEN}[OK] Direct IP connection successful")
    except httpx.ConnectTimeout:
        print(f"{Fore.RED}[FAIL] Connection timeout to Telegram IP")
        print(f"{Fore.YELLOW}  Your firewall or ISP might be blocking Telegram")
        return False
    except Exception as e:
        print(f"{Fore.YELLOW}[WARNING] Could not test direct IP: {e}")
    
    return True

def suggest_solutions(results):
    """Suggest solutions based on test results"""
    print_header("DIAGNOSIS & SOLUTIONS")
    
    if not results['internet']:
        print(f"{Fore.RED}Problem: No Internet Connection")
        print(f"{Fore.YELLOW}Solutions:")
        print("  1. Check your network cable/WiFi")
        print("  2. Restart your router")
        print("  3. Check if other websites work")
        print("  4. Contact your ISP")
        return
    
    if not results['telegram_api']:
        print(f"{Fore.RED}Problem: Cannot Reach Telegram API")
        print(f"{Fore.YELLOW}Solutions:")
        print("  1. Disable VPN temporarily")
        print("  2. Check Windows Firewall settings")
        print("  3. Check antivirus settings")
        print("  4. Try different network (mobile hotspot)")
        print("  5. Your country might be blocking Telegram")
        print(f"\n{Fore.CYAN}To run bot without Telegram:")
        print("  - Bot will still scan markets and work")
        print("  - Just won't send notifications")
        print("  - Start with: python main.py")
        return
    
    if not results['dns']:
        print(f"{Fore.RED}Problem: DNS Resolution Failed")
        print(f"{Fore.YELLOW}Solutions:")
        print("  1. Change DNS to 8.8.8.8 (Google)")
        print("  2. Flush DNS cache: ipconfig /flushdns")
        print("  3. Restart your computer")
        return
    
    if not results['bot_token']:
        print(f"{Fore.RED}Problem: Invalid Bot Token")
        print(f"{Fore.YELLOW}Solutions:")
        print("  1. Open .env file")
        print("  2. Get new token from @BotFather in Telegram")
        print("  3. Replace TELEGRAM_BOT_TOKEN value")
        print("  4. Make sure no extra spaces or quotes")
        return
    
    print(f"{Fore.GREEN}All tests passed! Your connection should work.")
    print(f"\n{Fore.CYAN}If bot still fails:")
    print("  1. Try running as Administrator")
    print("  2. Temporarily disable antivirus")
    print("  3. Wait a few minutes and try again")

async def main():
    print(Fore.CYAN + Style.BRIGHT + """
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║       TELEGRAM CONNECTION DIAGNOSTIC TOOL                     ║
    ║                                                               ║
    ║       Tests network connectivity to Telegram API              ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    results = {
        'internet': False,
        'telegram_api': False,
        'dns': False,
        'bot_token': False,
        'firewall': False
    }
    
    # Run all tests
    results['internet'] = await test_internet_connection()
    
    if results['internet']:
        results['dns'] = await test_dns_resolution()
        results['telegram_api'] = await test_telegram_api()
        
        if results['telegram_api']:
            results['bot_token'] = await test_bot_token()
            results['firewall'] = await test_firewall()
    
    # Summary
    print_header("TEST SUMMARY")
    
    tests = [
        ("Internet Connection", results['internet']),
        ("DNS Resolution", results['dns']),
        ("Telegram API Access", results['telegram_api']),
        ("Bot Token Valid", results['bot_token']),
        ("Firewall Check", results['firewall'])
    ]
    
    all_passed = True
    for test_name, passed in tests:
        status = f"{Fore.GREEN}PASS" if passed else f"{Fore.RED}FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    # Suggestions
    suggest_solutions(results)
    
    if all_passed:
        print(f"\n{Fore.GREEN}✓ Ready to run bot!")
    else:
        print(f"\n{Fore.RED}× Some tests failed. Fix issues above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        input("\nPress Enter to exit...")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(Fore.RED + f"\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)