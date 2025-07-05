# Azure Cost Anomaly Alert Manager

A Python-based command-line tool for managing Azure Cost Management anomaly alerts across multiple subscriptions. This tool helps you automatically detect and create cost anomaly alerts for Azure subscriptions, ensuring you stay informed about unexpected cost spikes.

<img width="862" alt="image" src="https://github.com/user-attachments/assets/c743eb76-d6c5-4720-b39e-b380a0b61369" />


## Features

- 🔍 **Automatic Subscription Discovery**: Scans all active Azure subscriptions in your tenant
- 🚀 **Bulk Alert Creation**: Create anomaly alerts for all subscriptions at once
- 🎯 **Selective Alert Management**: Choose specific subscriptions for alert creation
- 📊 **Alert Status Monitoring**: Check existing alerts and their expiration dates
- ⚠️ **Expired Alert Detection**: Identify subscriptions with expired alerts
- 🤖 **Automated Mode**: Run in unattended mode with command-line arguments
- 🔄 **Smart Alert Replacement**: Automatically replaces expired alerts with new ones
- 🛡️ **Enhanced Error Handling**: Comprehensive retry logic and error recovery
- 📈 **Extended Alert Duration**: 5-year alert validity period for long-term monitoring
- 🎭 **Active Subscription Filtering**: Only processes active/enabled subscriptions
- 🔧 **Token Management**: Automatic token refresh and caching for optimal performance

## Prerequisites

- Python 3.7+
- Azure CLI or Azure credentials configured
- Required Python packages (see Installation section)
- Azure subscription with Cost Management access

## Installation

1. Clone or download the script
2. Install required Python packages:

```bash
pip install requests azure-identity
```

3. Ensure you have Azure authentication configured:
   - Azure CLI: `az login`
   - Service Principal credentials
   - Managed Identity (if running on Azure)

## Usage

### Interactive Mode (Default)

Run the script without arguments to enter interactive mode:

```bash
python main.py
```

The interactive menu provides the following options:

1. **Display Available Subscriptions** - List all active subscriptions with status
2. **Create Alerts for All Subscriptions** - Automatically create alerts for all subscriptions
3. **Create Alerts for Selected Subscriptions** - Choose specific subscriptions
4. **Check Existing Alerts** - Review current alert configurations with expiration details
5. **Display Subscriptions with Expired Alerts** - Find subscriptions needing attention
6. **Clear Screen** - Clear the terminal display
7. **Exit** - Quit the application

### Automated Mode

Run the script with command-line arguments for unattended operation:

```bash
# Create alerts with default settings
python main.py --auto-create-alerts

# Create alerts with custom configuration
python main.py --auto-create-alerts --alert-name "MyCustomAlert" --emails "admin@company.com,ops@company.com"
```

#### Command-Line Arguments

- `--auto-create-alerts`: Enable automatic alert creation mode
- `--alert-name`: Custom name for the alert (default: "dailyAnomalyByResource")
- `--emails`: Comma-separated email addresses for notifications (default: "cloudarea@kruksa.pl")

### Examples

```bash
# Interactive mode
python main.py

# Auto mode with defaults
python main.py --auto-create-alerts

# Auto mode with custom settings
python main.py --auto-create-alerts --alert-name "ProductionAlerts" --emails "devops@company.com,finance@company.com"
```

## How It Works

### Alert Creation Process

1. **Subscription Discovery**: The tool fetches all active Azure subscriptions
2. **Alert Scanning**: Checks each subscription for existing Cost Management alerts
3. **Status Analysis**: Categorizes subscriptions as:
   - ✅ No alerts (ready for creation)
   - 🔄 Expired alerts (ready for replacement)
   - ⏭️ Valid alerts (skip)
   - ❌ Errors/Inactive (skip)
4. **Alert Creation**: Creates new anomaly alerts for subscriptions that need them
5. **Results Summary**: Provides detailed results of the operation

### Enhanced Alert Management

The tool now includes advanced features:
- **Smart Detection**: Identifies both missing and expired alerts
- **Batch Processing**: Processes subscriptions in configurable batches (default: 10)
- **Automatic Replacement**: Replaces expired alerts with new 5-year validity periods
- **Real-time Status Checks**: Verifies subscription status before processing
- **Comprehensive Logging**: Detailed progress reporting with color-coded status

### Alert Configuration

Each created alert includes:
- **Type**: Cost Anomaly (InsightAlert)
- **Frequency**: Daily
- **Duration**: 5 years (1825 days) from creation
- **Scope**: Resource group level anomaly detection
- **Status**: Enabled
- **Notifications**: Email alerts to specified recipients
- **Subject**: "Cost anomaly detected in the resource"
- **Display Name**: "Daily anomaly by resource"

### Authentication & Performance

The tool uses Azure's `DefaultAzureCredential` with enhanced features:
- **Token Caching**: Caches tokens for 50 minutes to reduce API calls
- **Automatic Refresh**: Refreshes expired tokens automatically
- **Retry Logic**: Implements exponential backoff for failed requests
- **Connection Pooling**: Reuses HTTP connections for better performance

## Error Handling

The tool includes comprehensive error handling:
- **API Rate Limiting**: Implements retry logic with exponential backoff (3 attempts)
- **Network Issues**: Handles connection timeouts and retries with progressive delays
- **Authentication**: Provides clear error messages for auth failures
- **Subscription Access**: Skips subscriptions with insufficient permissions
- **Token Refresh**: Automatically refreshes expired Azure tokens
- **Inactive Subscriptions**: Filters out disabled/inactive subscriptions automatically
- **Batch Processing**: Processes subscriptions in batches to avoid API overload

## Output Examples

### Enhanced Scan Results
```
📊 SCAN RESULTS:
  ✅ No alerts (ready):         15
  🔄 Expired alerts (ready):    3
  ⏭️ Valid alerts (skip):       8
  ❌ Errors/Inactive:           2
  🎯 Total needing alerts:      18

🎉 FINAL RESULTS:
  ✅ Successfully created:      18
  ❌ Failed to create:          0
  ⏭️ Already had valid alerts: 8
  🚫 Skipped (errors):          2
```

### Detailed Alert Status Check
```
📋 Production Subscription (Enabled)
    ✅ dailyAnomalyByResource | Status: Enabled | Remaining: 1,787 days
    ✅ weeklyBudgetAlert | Status: Enabled | Remaining: 45 days

🔄 Development Subscription (Enabled)
    ⚠️ dailyAnomalyByResource | Status: Enabled | Remaining: -15 days (EXPIRED)
    ✅ monthlyBudgetAlert | Status: Enabled | Remaining: 120 days

❌ Test Subscription (Enabled) - No Cost Anomaly alerts
```

### Real-time Processing
```
🔄 Processing: Production Environment Subscription
  ✅ Successfully created new alert

🔄 Processing: Development Subscription  
  ✅ Successfully replaced expired alert

🔄 Processing: Staging Subscription
  ❌ Subscription became inactive
```

## Configuration

### Default Settings

- **Alert Name**: "dailyAnomalyByResource"
- **Email Recipients**: "NONE"
- **Alert Duration**: 5 years (1825 days)
- **Batch Size**: 10 subscriptions per batch
- **Retry Attempts**: 3 attempts for failed operations
- **Token Cache**: 50 minutes validity
- **Request Timeout**: 30 seconds

### Advanced Configuration

You can modify the following in the script:
- Default email addresses
- Alert display name and subject
- Processing batch sizes
- Retry configurations and delays
- Color schemes for output
- Token cache duration
- API timeout values

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Ensure Azure CLI is logged in: `az login`
   - Check if your account has proper permissions
   - Verify token refresh is working

2. **Permission Errors**
   - Verify Cost Management Contributor role
   - Check subscription access permissions
   - Ensure Microsoft.CostManagement provider is registered

3. **API Rate Limits**
   - The tool automatically handles rate limiting
   - Reduce batch sizes if needed
   - Check for concurrent operations

4. **Network Issues**
   - Check internet connectivity
   - Verify Azure service availability
   - Check firewall/proxy settings

5. **Subscription Issues**
   - Ensure subscriptions are in 'Enabled' state
   - Check for subscription state changes during processing
   - Verify access to Cost Management APIs

### Debug Mode

For detailed debugging of specific subscriptions, you can use the debug function:

```python
debug_subscription_alerts("subscription-id-here")
```

### Performance Optimization

- **Batch Processing**: Subscriptions are processed in batches of 10
- **Token Caching**: Reduces authentication overhead
- **Connection Pooling**: Reuses HTTP connections
- **Smart Filtering**: Only processes active subscriptions
- **Progress Delays**: Small delays between operations to prevent API overload

## Security Considerations

- Never hardcode credentials in the script
- Use environment variables for sensitive information
- Regularly rotate service principal credentials
- Monitor alert email destinations for accuracy
- Implement proper RBAC for Cost Management access
- Use managed identities when running on Azure resources
- Regularly review and update alert configurations

## API Compatibility

- **Azure Cost Management API**: Version 2022-10-01
- **Azure Resource Manager API**: Version 2022-12-01
- **Supported Alert Types**: InsightAlert (Cost Anomaly)
- **Supported Scopes**: Subscription level with resource group views

## Contributing

Feel free to contribute improvements:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with multiple subscriptions
5. Submit a pull request

### Development Guidelines

- Follow existing code style and patterns
- Add appropriate error handling
- Include progress indicators for long operations
- Test with both active and inactive subscriptions
- Maintain backward compatibility

## Version History

### Latest Updates
- ✨ Extended alert duration to 5 years for long-term monitoring
- 🔄 Added automatic replacement of expired alerts
- 🛡️ Enhanced error handling and retry logic
- 📊 Improved status reporting and categorization
- 🎭 Added active subscription filtering
- 🔧 Implemented token caching and automatic refresh
- 🚀 Added batch processing for better performance
- 📈 Enhanced progress reporting with real-time updates

## License

This tool is provided as-is for educational and operational purposes. Please ensure compliance with your organization's Azure usage policies.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review Azure Cost Management documentation
3. Verify your Azure permissions and access
4. Check Azure service health status
5. Review the tool's error messages and logs
