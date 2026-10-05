import 'package:shared_preferences/shared_preferences.dart';

class ApiConfig {
  // Update these with your actual FastAPI backend credentials
  // Local Development (Android Emulator uses 10.0.2.2 to access host localhost)
  // Using local IP for better connectivity: 192.168.1.196:8000
  // For Android Emulator, you can also try: http://10.0.2.2:8000
  static const String baseUrl = "https://brick-bhatta-backend-745155014095.asia-south1.run.app";
  static const String apiKey = "brick_bhatta_123"; 
  static const String tenantId = "kiln-001"; 
  
  // API Headers - includes the JWT if the user is logged in
  static Future<Map<String, String>> get headers async {
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'X-API-KEY': apiKey,
      'X-Tenant-ID': tenantId,
    };

    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('authToken');
    if (token != null && token.isNotEmpty) {
      headers['Authorization'] = 'Bearer $token';
    }

    return headers;
  }

  // API Endpoints (with trailing slashes to avoid 307 redirects)
  static const String namesEndpoint = '/names/'; // Trailing slash to avoid FastAPI redirects
  static const String usersEndpoint = '/users/';
  static const String salesEndpoint = '/sales/';
  static const String workEndpoint = '/work/';
  static const String transactionsEndpoint = '/transactions/';
  static const String healthEndpoint = '/health'; // No trailing slash for health endpoint
  
  // Full URLs
  static String get namesUrl => '$baseUrl$namesEndpoint';
  static String get usersUrl => '$baseUrl$usersEndpoint';
  static String get salesUrl => '$baseUrl$salesEndpoint';
  static String get workUrl => '$baseUrl$workEndpoint';
  static String get transactionsUrl => '$baseUrl$transactionsEndpoint';
  static String get healthUrl => '$baseUrl$healthEndpoint';
  
  // Helper methods
  static String getNameUrl(String id) => '$namesUrl/$id';
  static String getUserUrl(String id) => '$usersUrl/$id';
  static String getSaleUrl(String id) => '$salesUrl/$id';
  static String getWorkUrl(String id) => '$workUrl/$id';
  static String getTransactionUrl(String id) => '$transactionsUrl/$id';
}
