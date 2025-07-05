import requests
import json
from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta, timezone
import os
import sys
import argparse
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ANSI color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    MAGENTA = '\033[95m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_BLUE = '\033[94m'

# Global variables for token caching
_cached_token = None
_token_expiry = None
_credential = None

# Configure requests session with retry strategy
def get_requests_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

# ASCII Art and visual enhancements
def print_header():
    ascii_art = r"""
 $$$$$$\                        $$\            $$$$$$\                                              $$\           
$$  __$$\                       $$ |          $$  __$$\                                             $$ |          
$$ /  \__| $$$$$$\   $$$$$$$\ $$$$$$\         $$ /  $$ |$$$$$$$\   $$$$$$\  $$$$$$\$$$$\   $$$$$$\  $$ |$$\   $$\ 
$$ |      $$  __$$\ $$  _____|\_$$  _|        $$$$$$$$ |$$  __$$\ $$  __$$\ $$  _$$  _$$\  \____$$\ $$ |$$ |  $$ |
$$ |      $$ /  $$ |\$$$$$$\    $$ |          $$  __$$ |$$ |  $$ |$$ /  $$ |$$ / $$ / $$ | $$$$$$$ |$$ |$$ |  $$ |
$$ |  $$\ $$ |  $$ | \____$$\   $$ |$$\       $$ |  $$ |$$ |  $$ |$$ |  $$ |$$ | $$ | $$ |$$  __$$ |$$ |$$ |  $$ |
\$$$$$$  |\$$$$$$  |$$$$$$$  |  \$$$$  |      $$ |  $$ |$$ |  $$ |\$$$$$$  |$$ | $$ | $$ |\$$$$$$$ |$$ |\$$$$$$$ |
 \______/  \______/ \_______/    \____/       \__|  \__|\__|  \__| \______/ \__| \__| \__| \_______|\__| \____$$ |
                                                                                                        $$\   $$ |
                                                                                                        \$$$$$$  |
                                                                                                         \______/ 
"""
    print(f"{Colors.CYAN}{ascii_art}{Colors.RESET}")

def print_success_box(message):
    print(f"""
{Colors.GREEN}🎉 {message}{Colors.RESET}
""")

def print_error_box(message):
    print(f"""
{Colors.RED}❌ {message}{Colors.RESET}
""")

def print_warning_box(message):
    print(f"""
{Colors.YELLOW}⚠️  {message}{Colors.RESET}
""")

def print_info_box(message):
    print(f"""
{Colors.CYAN}ℹ️  {message}{Colors.RESET}
""")

def print_section_header(title):
    print(f"""
{Colors.BOLD}{Colors.CYAN}
{'='*80}
  {title}
{'='*80}
{Colors.RESET}""")

def print_loading_animation():
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    for i in range(20):
        print(f"\r{Colors.CYAN}🔄 Loading {frames[i % len(frames)]} Connecting to Azure...{Colors.RESET}", end='', flush=True)
        time.sleep(0.1)
    print(f"\r{Colors.GREEN}✅ Connected to Azure successfully!{Colors.RESET}")

# Initialize Azure connection (called once at startup)
def initialize_azure_connection():
    global _credential
    print_loading_animation()
    try:
        _credential = DefaultAzureCredential()
        # Test the connection by getting a token
        _credential.get_token("https://management.azure.com/.default")
        print_info_box("Azure connection initialized and verified")
    except Exception as e:
        print_error_box(f"Failed to initialize Azure connection: {str(e)}")
        sys.exit(1)

# Get access token with caching and error handling
def get_access_token():
    global _cached_token, _token_expiry, _credential
    
    # Check if we have a valid cached token
    if _cached_token and _token_expiry and datetime.now(timezone.utc) < _token_expiry:
        return _cached_token
    
    # Get new token with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if _credential is None:
                _credential = DefaultAzureCredential()
            
            token_response = _credential.get_token("https://management.azure.com/.default")
            _cached_token = token_response.token
            # Set expiry time to 50 minutes from now (tokens usually last 1 hour)
            _token_expiry = datetime.now(timezone.utc) + timedelta(minutes=50)
            
            return _cached_token
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"{Colors.YELLOW}⚠️  Token refresh attempt {attempt + 1} failed, retrying...{Colors.RESET}")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print_error_box(f"Failed to get access token after {max_retries} attempts: {str(e)}")
                raise

# Enhanced function to make Azure API calls with retry logic
def make_azure_api_call(url, method="GET", headers=None, data=None, timeout=30):
    """Make Azure API call with retry logic and error handling"""
    session = get_requests_session()
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if method.upper() == "GET":
                response = session.get(url, headers=headers, timeout=timeout)
            elif method.upper() == "PUT":
                response = session.put(url, headers=headers, data=data, timeout=timeout)
            else:
                response = session.request(method, url, headers=headers, data=data, timeout=timeout)
            
            return response
            
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                requests.exceptions.ReadTimeout) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"{Colors.YELLOW}⚠️  Connection error on attempt {attempt + 1}, retrying in {wait_time}s...{Colors.RESET}")
                time.sleep(wait_time)
            else:
                raise e
        except Exception as e:
            print_error_box(f"Unexpected error in API call: {str(e)}")
            raise e

# Function to get subscriptions from Azure with status filtering
def get_subscriptions(include_inactive=False):
    try:
        access_token = get_access_token()
        url = "https://management.azure.com/subscriptions?api-version=2022-12-01"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = make_azure_api_call(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            subscriptions = []
            
            for sub in data['value']:
                subscription_info = {
                    'id': sub['subscriptionId'], 
                    'name': sub['displayName'],
                    'state': sub.get('state', 'Unknown')
                }
                
                # Only include active subscriptions unless specifically requested
                if include_inactive or subscription_info['state'] == 'Enabled':
                    subscriptions.append(subscription_info)
            
            return subscriptions
        else:
            print(f"{Colors.RED}Failed to get subscriptions. Status code: {response.status_code}{Colors.RESET}")
            return []
            
    except Exception as e:
        print_error_box(f"Error getting subscriptions: {str(e)}")
        return []

# Function to check if subscription is active
def is_subscription_active(subscription_id):
    try:
        access_token = get_access_token()
        url = f"https://management.azure.com/subscriptions/{subscription_id}?api-version=2022-12-01"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = make_azure_api_call(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('state') == 'Enabled'
        else:
            print(f"{Colors.RED}Error checking subscription {subscription_id} status: {response.status_code}{Colors.RESET}")
            return False
            
    except Exception as e:
        print(f"{Colors.RED}Exception checking subscription {subscription_id}: {str(e)}{Colors.RESET}")
        return False

# Function to create cost anomaly alert
def create_cost_anomaly_alert(subscription_id, alert_name, emails):
    access_token = get_access_token()
    url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/scheduledActions/{alert_name}?api-version=2022-10-01"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    # Set dates - changed from 365 days to 5 years (1825 days)
    start_date = datetime.now(timezone.utc).replace(microsecond=0)
    end_date = (start_date + timedelta(days=1825)).replace(microsecond=0)  # 5 years = 365 * 5 = 1825 days
    
    alert_body = {
        "kind": "InsightAlert",
        "properties": {
            "displayName": "Daily anomaly by resource",
            "notification": {
                "to": emails,
                "subject": "Cost anomaly detected in the resource"
            },
            "schedule": {
                "frequency": "Daily",
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat()
            },
            "status": "Enabled",
            "viewId": f"/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/views/ms:DailyAnomalyByResourceGroup"
        }
    }

    response = requests.put(url, headers=headers, data=json.dumps(alert_body))
    
    if response.status_code == 201 or response.status_code == 200:
        print(f"{Colors.GREEN}Alert successfully created for subscription {subscription_id}{Colors.RESET}")
    else:
        print(f"{Colors.RED}Failed to create alert for subscription {subscription_id}. Status code: {response.status_code}, Response: {response.text}{Colors.RESET}")

# Function to create alerts for all subscriptions (updated)
def create_alerts_for_all_subscriptions(alert_name=None, emails=None, auto_mode=False):
    print_section_header("CREATE ALERTS FOR ALL SUBSCRIPTIONS")
    
    try:
        if not auto_mode:
            alert_name = input(f"{Colors.YELLOW}🏷️  Enter alert name (default: dailyAnomalyByResource): {Colors.RESET}").strip()
            if not alert_name:
                alert_name = "dailyAnomalyByResource"
            
            emails_input = input(f"{Colors.YELLOW}📧 Enter email addresses (separated by commas): {Colors.RESET}").strip()
            if not emails_input:
                emails = ["your@email.com"]
            else:
                emails = [email.strip() for email in emails_input.split(",")]
        else:
            if not alert_name:
                alert_name = "dailyAnomalyByResource"
            if not emails:
                emails = ["your@email.com"]
        
        subscriptions = get_subscriptions(include_inactive=False)
        
        if not subscriptions:
            print_error_box("No available active subscriptions")
            return False
        
        print_section_header("SCANNING FOR EXISTING ALERTS")
        print(f"{Colors.CYAN}🔍 Scanning {len(subscriptions)} active subscriptions...\n{Colors.RESET}")
        
        access_token = get_access_token()
        current_date = datetime.now(timezone.utc)
        subscriptions_without_alerts = []
        subscriptions_with_valid_alerts = []
        subscriptions_with_expired_alerts = []
        subscription_errors = []
        
        # Process subscriptions in smaller batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(subscriptions), batch_size):
            batch = subscriptions[i:i + batch_size]
            
            for subscription in batch:
                try:
                    if not is_subscription_active(subscription['id']):
                        print(f"{Colors.RED}  ❌ {subscription['name'][:60]} - Inactive subscription{Colors.RESET}")
                        subscription_errors.append(subscription)
                        continue
                    
                    url = f"https://management.azure.com/subscriptions/{subscription['id']}/providers/Microsoft.CostManagement/scheduledActions?api-version=2022-10-01"
                    
                    headers = {
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    }
                    
                    response = make_azure_api_call(url, headers=headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        anomaly_alerts = [alert for alert in data.get('value', []) if alert.get('kind') == 'InsightAlert']
                        
                        if not anomaly_alerts:
                            # No alerts at all
                            subscriptions_without_alerts.append(subscription)
                            print(f"{Colors.GREEN}  ✅ {subscription['name'][:60]} - No alerts, ready for creation{Colors.RESET}")
                        else:
                            # Check if any alerts are still valid (not expired)
                            has_valid_alerts = False
                            expired_count = 0
                            
                            for alert in anomaly_alerts:
                                end_date_str = alert.get('properties', {}).get('schedule', {}).get('endDate')
                                
                                if end_date_str:
                                    try:
                                        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                                        days_remaining = (end_date - current_date).days
                                        
                                        if days_remaining > 0:
                                            has_valid_alerts = True
                                        else:
                                            expired_count += 1
                                    except ValueError:
                                        # Invalid date format, treat as expired
                                        expired_count += 1
                                else:
                                    # No end date, treat as expired
                                    expired_count += 1
                            
                            if has_valid_alerts:
                                subscriptions_with_valid_alerts.append(subscription)
                                print(f"{Colors.YELLOW}  ⏭️  {subscription['name'][:60]} - Has valid alerts ({len(anomaly_alerts)} total, {expired_count} expired){Colors.RESET}")
                            else:
                                # All alerts are expired, needs new alert
                                subscriptions_with_expired_alerts.append(subscription)
                                print(f"{Colors.CYAN}  🔄 {subscription['name'][:60]} - All alerts expired ({expired_count} total), ready for new alert{Colors.RESET}")
                    else:
                        print(f"{Colors.RED}  ❌ {subscription['name'][:60]} - Error: {response.status_code}{Colors.RESET}")
                        subscription_errors.append(subscription)
                        
                except Exception as e:
                    print(f"{Colors.RED}  ❌ {subscription['name'][:60]} - Exception: {str(e)}{Colors.RESET}")
                    subscription_errors.append(subscription)
            
            # Small delay between batches to prevent overwhelming the API
            if i + batch_size < len(subscriptions):
                time.sleep(1)
        
        # Combine subscriptions that need alerts (no alerts + expired alerts)
        subscriptions_needing_alerts = subscriptions_without_alerts + subscriptions_with_expired_alerts
        
        print(f"""
{Colors.CYAN}📊 SCAN RESULTS:{Colors.RESET}
{Colors.GREEN}  ✅ No alerts (ready):         {len(subscriptions_without_alerts)}{Colors.RESET}
{Colors.CYAN}  🔄 Expired alerts (ready):    {len(subscriptions_with_expired_alerts)}{Colors.RESET}
{Colors.YELLOW}  ⏭️  Valid alerts (skip):       {len(subscriptions_with_valid_alerts)}{Colors.RESET}
{Colors.RED}  ❌ Errors/Inactive:           {len(subscription_errors)}{Colors.RESET}
{Colors.BOLD}{Colors.WHITE}  🎯 Total needing alerts:       {len(subscriptions_needing_alerts)}{Colors.RESET}
""")
        
        if not subscriptions_needing_alerts:
            print_warning_box("All active subscriptions already have valid alerts or had errors")
            return True
        
        print_section_header("ALERT CREATION CONFIGURATION")
        print(f"{Colors.CYAN}🏷️  Alert name: {Colors.WHITE}{alert_name}{Colors.RESET}")
        print(f"{Colors.CYAN}📧 Email addresses: {Colors.WHITE}{', '.join(emails)}{Colors.RESET}")
        print(f"{Colors.CYAN}🎯 Target subscriptions: {Colors.WHITE}{len(subscriptions_needing_alerts)}{Colors.RESET}")
        
        if subscriptions_with_expired_alerts:
            print(f"{Colors.YELLOW}⚠️  Note: {len(subscriptions_with_expired_alerts)} subscriptions have expired alerts that will be replaced{Colors.RESET}")
        
        if not auto_mode:
            confirm = input(f"\n{Colors.YELLOW}🚀 Create alerts for {len(subscriptions_needing_alerts)} subscriptions? (y/n): {Colors.RESET}").strip().lower()
            if confirm != 'y':
                print_warning_box("Operation cancelled by user")
                return False
        else:
            print(f"\n{Colors.CYAN}🤖 Auto mode: Creating alerts for {len(subscriptions_needing_alerts)} subscriptions...{Colors.RESET}")
        
        print_section_header("CREATING ALERTS")
        successful_creates = 0
        failed_creates = 0
        
        for subscription in subscriptions_needing_alerts:
            try:
                print(f"\n{Colors.CYAN}🔄 Processing: {subscription['name']}{Colors.RESET}")
                
                if not is_subscription_active(subscription['id']):
                    print(f"{Colors.RED}  ❌ Subscription became inactive{Colors.RESET}")
                    failed_creates += 1
                    continue
                
                access_token = get_access_token()
                url = f"https://management.azure.com/subscriptions/{subscription['id']}/providers/Microsoft.CostManagement/scheduledActions/{alert_name}?api-version=2022-10-01"
                
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                
                start_date = datetime.now(timezone.utc).replace(microsecond=0)
                end_date = (start_date + timedelta(days=1825)).replace(microsecond=0)  # 5 years = 365 * 5 = 1825 days
                
                alert_body = {
                    "kind": "InsightAlert",
                    "properties": {
                        "displayName": "Daily anomaly by resource",
                        "notification": {
                            "to": emails,
                            "subject": "Cost anomaly detected in the resource"
                        },
                        "schedule": {
                            "frequency": "Daily",
                            "startDate": start_date.isoformat(),
                            "endDate": end_date.isoformat()
                        },
                        "status": "Enabled",
                        "viewId": f"/subscriptions/{subscription['id']}/providers/Microsoft.CostManagement/views/ms:DailyAnomalyByResourceGroup"
                    }
                }

                response = make_azure_api_call(url, method="PUT", headers=headers, data=json.dumps(alert_body))
                
                if response.status_code == 201 or response.status_code == 200:
                    is_replacement = subscription in subscriptions_with_expired_alerts
                    action_text = "replaced expired alert" if is_replacement else "created new alert"
                    print(f"{Colors.GREEN}  ✅ Successfully {action_text}{Colors.RESET}")
                    successful_creates += 1
                else:
                    print(f"{Colors.RED}  ❌ Failed to create alert (Status: {response.status_code}){Colors.RESET}")
                    failed_creates += 1
                    
            except Exception as e:
                print(f"{Colors.RED}  ❌ Exception creating alert: {str(e)}{Colors.RESET}")
                failed_creates += 1
            
            # Small delay between alert creations
            time.sleep(0.5)
        
        print(f"""
{Colors.CYAN}🎉 FINAL RESULTS:{Colors.RESET}
{Colors.GREEN}  ✅ Successfully created:      {successful_creates}{Colors.RESET}
{Colors.RED}  ❌ Failed to create:          {failed_creates}{Colors.RESET}
{Colors.YELLOW}  ⏭️  Already had valid alerts: {len(subscriptions_with_valid_alerts)}{Colors.RESET}
{Colors.RED}  🚫 Skipped (errors):          {len(subscription_errors)}{Colors.RESET}
""")
        
        return successful_creates > 0 or len(subscriptions_with_valid_alerts) > 0
        
    except Exception as e:
        print_error_box(f"Critical error in create_alerts_for_all_subscriptions: {str(e)}")
        return False

# Function to create alert for selected subscriptions (updated)
def create_alert_for_selected_subscriptions():
    # Only show active subscriptions for selection
    subscriptions = get_subscriptions(include_inactive=False)
    
    if not subscriptions:
        print_error_box("No available active subscriptions")
        return
    
    print_section_header("SELECT SUBSCRIPTIONS (ACTIVE ONLY)")
    for i, sub in enumerate(subscriptions, 1):
        print(f"{Colors.WHITE}  {i:2d}. {sub['name'][:60]} ({sub['id']}) - {sub['state']}{Colors.RESET}")
    
    print(f"\n{Colors.CYAN}💡 Enter subscription numbers separated by commas (e.g., 1,3,5) or 'all' for all active subscriptions{Colors.RESET}")
    choice_input = input(f"{Colors.YELLOW}🎯 Selection: {Colors.RESET}").strip()
    
    selected_subscriptions = []
    
    if choice_input.lower() == 'all':
        selected_subscriptions = subscriptions
    else:
        try:
            choices = [int(x.strip()) for x in choice_input.split(',')]
            for choice in choices:
                if 1 <= choice <= len(subscriptions):
                    selected_subscriptions.append(subscriptions[choice - 1])
                else:
                    print_error_box(f"Invalid choice: {choice}. Skipping.")
        except ValueError:
            print_error_box("Invalid input format. Please use numbers separated by commas.")
            return
    
    if not selected_subscriptions:
        print_error_box("No valid subscriptions selected")
        return
    
    print_section_header("SELECTED SUBSCRIPTIONS")
    for sub in selected_subscriptions:
        print(f"{Colors.GREEN}  • {sub['name'][:60]} ({sub['id']}) - {sub['state']}{Colors.RESET}")
    
    # Check if alerts already exist for selected subscriptions
    print_section_header("CHECKING EXISTING ALERTS")
    print(f"{Colors.CYAN}🔍 Checking {len(selected_subscriptions)} selected subscriptions for existing alerts...\n{Colors.RESET}")
    
    access_token = get_access_token()
    subscriptions_without_alerts = []
    subscriptions_with_alerts = []
    subscription_errors = []
    
    for subscription in selected_subscriptions:
        # Double-check subscription status before processing
        if not is_subscription_active(subscription['id']):
            print(f"{Colors.RED}  ❌ {subscription['name'][:60]} - Subscription is not active, skipping{Colors.RESET}")
            subscription_errors.append(subscription)
            continue
            
        url = f"https://management.azure.com/subscriptions/{subscription['id']}/providers/Microsoft.CostManagement/scheduledActions?api-version=2022-10-01"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            anomaly_alerts = [alert for alert in data.get('value', []) if alert.get('kind') == 'InsightAlert']
            
            if anomaly_alerts:
                subscriptions_with_alerts.append(subscription)
                print(f"{Colors.YELLOW}  ⏭️  {subscription['name'][:60]} - Already has {len(anomaly_alerts)} alert(s){Colors.RESET}")
            else:
                subscriptions_without_alerts.append(subscription)
                print(f"{Colors.GREEN}  ✅ {subscription['name'][:60]} - No existing alerts{Colors.RESET}")
        else:
            print(f"{Colors.RED}  ❌ {subscription['name'][:60]} - Status: {response.status_code}{Colors.RESET}")
            subscription_errors.append(subscription)
    
    print(f"""
{Colors.CYAN}📊 SUMMARY:{Colors.RESET}
{Colors.GREEN}  ✅ Subscriptions without alerts: {len(subscriptions_without_alerts)}{Colors.RESET}
{Colors.YELLOW}  ⏭️  Subscriptions with existing alerts: {len(subscriptions_with_alerts)}{Colors.RESET}
{Colors.RED}  ❌ Subscriptions with errors/inactive: {len(subscription_errors)}{Colors.RESET}
""")
    
    if not subscriptions_without_alerts:
        print_warning_box("All selected subscriptions already have alerts configured or had errors. No action needed.")
        return
    
    # Get alert details from user
    print_section_header("ALERT CONFIGURATION")
    alert_name = input(f"{Colors.YELLOW}🏷️  Enter alert name (default: dailyAnomalyByResource): {Colors.RESET}").strip()
    if not alert_name:
        alert_name = "dailyAnomalyByResource"
    
    emails_input = input(f"{Colors.YELLOW}📧 Enter email addresses (separated by commas): {Colors.RESET}").strip()
    if not emails_input:
        emails = ["your@email.com"]
    else:
        emails = [email.strip() for email in emails_input.split(",")]
    
    # Create the alerts
    print_section_header("CREATING ALERTS")
    print(f"{Colors.CYAN}🏷️  Alert name: {Colors.WHITE}{alert_name}{Colors.RESET}")
    print(f"{Colors.CYAN}📧 Email addresses: {Colors.WHITE}{', '.join(emails)}{Colors.RESET}")
    print(f"{Colors.CYAN}🎯 Number of subscriptions to process: {Colors.WHITE}{len(subscriptions_without_alerts)}{Colors.RESET}")
    
    confirm = input(f"\n{Colors.YELLOW}🚀 Create alerts for {len(subscriptions_without_alerts)} subscriptions? (y/n): {Colors.RESET}").strip().lower()
    if confirm != 'y':
        print_warning_box("Operation cancelled")
        return
    
    successful_creates = 0
    failed_creates = 0
    
    for subscription in subscriptions_without_alerts:
        print(f"\n{Colors.CYAN}🔄 Processing: {subscription['name']}{Colors.RESET}")
        
        # Final check before creating alert
        if not is_subscription_active(subscription['id']):
            print(f"{Colors.RED}  ❌ Subscription became inactive, skipping{Colors.RESET}")
            failed_creates += 1
            continue
        
        # Use the existing function to create the alert
        access_token = get_access_token()
        url = f"https://management.azure.com/subscriptions/{subscription['id']}/providers/Microsoft.CostManagement/scheduledActions/{alert_name}?api-version=2022-10-01"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Set dates
        start_date = datetime.now(timezone.utc).replace(microsecond=0)
        end_date = (start_date + timedelta(days=1825)).replace(microsecond=0)  # 5 years = 365 * 5 = 1825 days
        
        alert_body = {
            "kind": "InsightAlert",
            "properties": {
                "displayName": "Daily anomaly by resource",
                "notification": {
                    "to": emails,
                    "subject": "Cost anomaly detected in the resource"
                },
                "schedule": {
                    "frequency": "Daily",
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat()
                },
                "status": "Enabled",
                "viewId": f"/subscriptions/{subscription['id']}/providers/Microsoft.CostManagement/views/ms:DailyAnomalyByResourceGroup"
            }
        }

        response = requests.put(url, headers=headers, data=json.dumps(alert_body))
        
        if response.status_code == 201 or response.status_code == 200:
            print(f"{Colors.GREEN}  ✅ Alert successfully created{Colors.RESET}")
            successful_creates += 1
        else:
            print(f"{Colors.RED}  ❌ Failed to create alert (Status: {response.status_code}){Colors.RESET}")
            failed_creates += 1
    
    print(f"""
{Colors.CYAN}🎉 FINAL RESULTS:{Colors.RESET}
{Colors.GREEN}  ✅ Successfully created: {successful_creates}{Colors.RESET}
{Colors.RED}  ❌ Failed to create: {failed_creates}{Colors.RESET}
{Colors.YELLOW}  ⏭️  Skipped (already had alerts): {len(subscriptions_with_alerts)}{Colors.RESET}
{Colors.RED}  🚫 Skipped (errors/inactive): {len(subscription_errors)}{Colors.RESET}
""")

# Function to check existing alerts (updated)
def check_existing_alerts():
    # Only check active subscriptions
    subscriptions = get_subscriptions(include_inactive=False)
    
    if not subscriptions:
        print_error_box("No available active subscriptions")
        return
    
    print_section_header("CHECKING EXISTING ALERTS (ACTIVE SUBSCRIPTIONS ONLY)")
    access_token = get_access_token()
    current_date = datetime.now(timezone.utc)
    
    for subscription in subscriptions:
        # Double-check subscription status
        if not is_subscription_active(subscription['id']):
            print(f"\n{Colors.RED}❌ {subscription['name'][:60]} - INACTIVE, skipping{Colors.RESET}")
            continue
            
        url = f"https://management.azure.com/subscriptions/{subscription['id']}/providers/Microsoft.CostManagement/scheduledActions?api-version=2022-10-01"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            anomaly_alerts = [alert for alert in data.get('value', []) if alert.get('kind') == 'InsightAlert']
            
            if anomaly_alerts:
                print(f"\n{Colors.CYAN}📋 {subscription['name'][:60]} ({subscription['state']}){Colors.RESET}")
                for alert in anomaly_alerts:
                    alert_name = alert.get('name', 'Unknown')
                    end_date_str = alert.get('properties', {}).get('schedule', {}).get('endDate')
                    status = alert.get('properties', {}).get('status', 'Unknown')
                    
                    if end_date_str:
                        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        days_remaining = (end_date - current_date).days
                        
                        if days_remaining > 0:
                            print(f"{Colors.GREEN}    ✅ {alert_name} | Status: {status} | Remaining: {days_remaining} days{Colors.RESET}")
                        else:
                            print(f"{Colors.RED}    ❌ {alert_name} | Status: {status} | Expired {abs(days_remaining)} days ago{Colors.RESET}")
                    else:
                        print(f"{Colors.YELLOW}    ⚠️  {alert_name} | Status: {status} | No end date{Colors.RESET}")
            else:
                print(f"\n{Colors.RED}❌ {subscription['name'][:60]} ({subscription['state']}) - No Cost Anomaly alerts{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}❌ Error checking {subscription['name'][:60]}: {response.status_code}{Colors.RESET}")

# Function to display subscriptions with expired alerts (updated)
def display_subscriptions_with_expired_alerts():
    # Only check active subscriptions
    subscriptions = get_subscriptions(include_inactive=False)
    
    if not subscriptions:
        print_error_box("No available active subscriptions")
        return
    
    print_section_header("SUBSCRIPTIONS WITH EXPIRED ALERTS (ACTIVE ONLY)")
    print(f"{Colors.CYAN}🔍 Checking {len(subscriptions)} active subscriptions for expired alerts...\n{Colors.RESET}")
    
    access_token = get_access_token()
    current_date = datetime.now(timezone.utc)
    expired_subscriptions = []
    expired_count = 0
    
    for i, subscription in enumerate(subscriptions, 1):
        # Double-check subscription status
        if not is_subscription_active(subscription['id']):
            print(f"{Colors.RED}❌ {subscription['name'][:60]} - Subscription is not active, skipping{Colors.RESET}")
            continue
            
        url = f"https://management.azure.com/subscriptions/{subscription['id']}/providers/Microsoft.CostManagement/scheduledActions?api-version=2022-10-01"
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            anomaly_alerts = [alert for alert in data.get('value', []) if alert.get('kind') == 'InsightAlert']
            
            has_expired_alerts = False
            for alert in anomaly_alerts:
                end_date_str = alert.get('properties', {}).get('schedule', {}).get('endDate')
                
                if end_date_str:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    days_remaining = (end_date - current_date).days
                    
                    if days_remaining <= 0:
                        has_expired_alerts = True
                        break
            
            if has_expired_alerts:
                expired_count += 1
                print(f"{Colors.RED}❌ [{expired_count}] {subscription['name'][:60]} - EXPIRED ALERTS!{Colors.RESET}")
                expired_subscriptions.append(subscription)
        else:
            # Show errors but don't count as expired
            print(f"{Colors.YELLOW}⚠️  {subscription['name'][:60]} - Error: {response.status_code}{Colors.RESET}")
    
    print(f"""
{Colors.CYAN}📊 RESULTS:{Colors.RESET}
{Colors.GREEN if not expired_subscriptions else Colors.RED}  Found {len(expired_subscriptions)} active subscriptions with expired alerts out of {len(subscriptions)} total active.{Colors.RESET}
""")

# Function to debug specific subscription alerts
def debug_subscription_alerts(subscription_id):
    access_token = get_access_token()
    url = f"https://management.azure.com/subscriptions/{subscription_id}/providers/Microsoft.CostManagement/scheduledActions?api-version=2022-10-01"
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        anomaly_alerts = [alert for alert in data.get('value', []) if alert.get('kind') == 'InsightAlert']
        
        print(f"\n{Colors.CYAN}=== DEBUG ALERTS FOR SUBSCRIPTION {subscription_id} ==={Colors.RESET}")
        print(f"{Colors.WHITE}Found {len(anomaly_alerts)} anomaly alerts:{Colors.RESET}")
        
        current_date = datetime.now(timezone.utc)
        
        for i, alert in enumerate(anomaly_alerts, 1):
            alert_name = alert.get('name', 'Unknown')
            start_date_str = alert.get('properties', {}).get('schedule', {}).get('startDate')
            end_date_str = alert.get('properties', {}).get('schedule', {}).get('endDate')
            status = alert.get('properties', {}).get('status', 'Unknown')
            
            print(f"\n{Colors.BLUE}Alert {i}:{Colors.RESET}")
            print(f"  Name: {alert_name}")
            print(f"  Status: {status}")
            print(f"  Start Date: {start_date_str}")
            print(f"  End Date: {end_date_str}")
            
            if end_date_str:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                days_remaining = (end_date - current_date).days
                
                if days_remaining > 0:
                    print(f"  {Colors.GREEN}Days remaining: {days_remaining}{Colors.RESET}")
                else:
                    print(f"  {Colors.RED}Expired {abs(days_remaining)} days ago{Colors.RESET}")
            else:
                print(f"  {Colors.YELLOW}No end date specified{Colors.RESET}")
    else:
        print(f"{Colors.RED}Error: {response.status_code}{Colors.RESET}")

# Function to display menu
def display_menu():
    # Remove print_header() from here since it's already shown once in main()
    print(f"""
{Colors.CYAN}🎛️  MAIN MENU{Colors.RESET}
{Colors.CYAN}{'='*50}{Colors.RESET}

{Colors.WHITE}  1. 📋 Display available subscriptions{Colors.RESET}
{Colors.WHITE}  2. 🚀 Create alerts for all subscriptions{Colors.RESET}
{Colors.WHITE}  3. 🎯 Create alerts for selected subscriptions{Colors.RESET}
{Colors.WHITE}  4. 🔍 Check existing alerts{Colors.RESET}
{Colors.WHITE}  5. ⚠️  Display subscriptions with expired alerts{Colors.RESET}
{Colors.WHITE}  6. 🧹 Clear screen{Colors.RESET}
{Colors.WHITE}  0. 🚪 Exit{Colors.RESET}

{Colors.CYAN}{'='*50}{Colors.RESET}
""")

# Function to clear screen
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

# Function to parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Azure Cost Anomaly Alert Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # Interactive mode
  python main.py --auto-create-alerts              # Auto create alerts with defaults
  python main.py --auto-create-alerts --alert-name "MyAlert" --emails "admin@company.com,ops@company.com"
        """
    )
    
    parser.add_argument(
        '--auto-create-alerts',
        action='store_true',
        help='Automatically create alerts for all subscriptions without existing alerts'
    )
    
    parser.add_argument(
        '--alert-name',
        type=str,
        default='dailyAnomalyByResource',
        help='Name of the alert to create (default: dailyAnomalyByResource)'
    )
    
    parser.add_argument(
        '--emails',
        type=str,
        default='',
        help='Comma-separated email addresses for notifications (default: none)'
    )
    
    return parser.parse_args()

# Main function with enhanced error handling
def main():
    try:
        args = parse_arguments()
        
        # Initialize Azure connection once at startup
        print_header()  # Show header only once here
        initialize_azure_connection()
        
        # Check if auto mode is requested
        if args.auto_create_alerts:
            print(f"""
{Colors.CYAN}🤖 AUTO MODE ACTIVATED{Colors.RESET}
{Colors.CYAN}{'='*50}{Colors.RESET}

{Colors.WHITE}🏷️  Alert name: {args.alert_name}{Colors.RESET}
{Colors.WHITE}📧 Email addresses: {args.emails}{Colors.RESET}
{Colors.WHITE}🎯 Mode: Automatic alert creation{Colors.RESET}

{Colors.CYAN}{'='*50}{Colors.RESET}
""")
            
            emails = [email.strip() for email in args.emails.split(",")]
            
            success = create_alerts_for_all_subscriptions(
                alert_name=args.alert_name,
                emails=emails,
                auto_mode=True
            )
            
            if success:
                print_success_box("Auto mode completed successfully!")
                sys.exit(0)
            else:
                print_error_box("Auto mode completed with errors!")
                sys.exit(1)
        
        # Interactive mode
        clear_screen()
        while True:
            display_menu()
            choice = input(f"{Colors.YELLOW}🎯 Select your option: {Colors.RESET}").strip()
            
            if choice == "1":
                clear_screen()
                display_subscriptions()
                input(f"\n{Colors.CYAN}⏎ Press Enter to continue...{Colors.RESET}")
                clear_screen()
                
            elif choice == "2":
                clear_screen()
                create_alerts_for_all_subscriptions()
                input(f"\n{Colors.CYAN}⏎ Press Enter to continue...{Colors.RESET}")
                clear_screen()
                
            elif choice == "3":
                clear_screen()
                create_alert_for_selected_subscriptions()
                input(f"\n{Colors.CYAN}⏎ Press Enter to continue...{Colors.RESET}")
                clear_screen()
                
            elif choice == "4":
                clear_screen()
                check_existing_alerts()
                input(f"\n{Colors.CYAN}⏎ Press Enter to continue...{Colors.RESET}")
                clear_screen()
                
            elif choice == "5":
                clear_screen()
                display_subscriptions_with_expired_alerts()
                input(f"\n{Colors.CYAN}⏎ Press Enter to continue...{Colors.RESET}")
                clear_screen()
                
            elif choice == "6":
                clear_screen()
                
            elif choice == "0":
                print(f"""
{Colors.GREEN}👋 Thank you for using Azure Cost Anomaly Alert Manager!{Colors.RESET}
{Colors.GREEN}🌟 Goodbye! 🌟{Colors.RESET}
""")
                break
                
            else:
                print_error_box("Invalid choice. Please select a valid option from the menu.")
                input(f"\n{Colors.CYAN}⏎ Press Enter to continue...{Colors.RESET}")
                clear_screen()
    
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️  Operation cancelled by user{Colors.RESET}")
        sys.exit(0)
    except Exception as e:
        print_error_box(f"Critical error: {str(e)}")
        sys.exit(1)

# Function to display subscriptions (missing from the code)
def display_subscriptions():
    subscriptions = get_subscriptions(include_inactive=False)
    
    if not subscriptions:
        print_error_box("No available active subscriptions")
        return
    
    print_section_header("ACTIVE SUBSCRIPTIONS")
    print(f"{Colors.CYAN}Found {len(subscriptions)} active subscriptions:\n{Colors.RESET}")
    
    for i, sub in enumerate(subscriptions, 1):
        print(f"{Colors.GREEN}  {i:3d}. {sub['name'][:60]} ({sub['id']}) - {sub['state']}{Colors.RESET}")

# Run main function
if __name__ == "__main__":
    main()
