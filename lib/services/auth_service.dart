import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../config/api_config.dart';

/// Phone + password authentication against the backend (JWT).
class AuthService {
  /// Log in and persist the JWT and user info. Throws an [Exception] with a
  /// user-presentable message on failure.
  Future<Map<String, dynamic>> login(String phoneNumber, String password) async {
    final http.Response response;
    try {
      response = await http
          .post(
            Uri.parse('${ApiConfig.baseUrl}/auth/login'),
            headers: {
              'Content-Type': 'application/json',
              'X-API-KEY': ApiConfig.apiKey,
              'X-Tenant-ID': ApiConfig.tenantId,
            },
            body: jsonEncode({'phone_number': phoneNumber, 'password': password}),
          )
          .timeout(const Duration(seconds: 30));
    } on SocketException {
      throw Exception('Cannot connect to server. Please check your internet connection.');
    } on TimeoutException {
      throw Exception('Server is not responding. Please try again.');
    }

    final body = jsonDecode(response.body);
    if (response.statusCode != 200) {
      throw Exception(body['detail'] ?? 'Login failed');
    }

    final user = body['user'] as Map<String, dynamic>;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('isAuthenticated', true);
    await prefs.setString('authToken', body['access_token']);
    await prefs.setString('userId', user['id'] ?? '');
    await prefs.setString('userName', user['name'] ?? '');
    await prefs.setString('userNameHindi', user['name_hindi'] ?? user['name'] ?? '');
    await prefs.setString('userRole', user['role'] ?? '');
    await prefs.setString('userRoleHindi', user['role_hindi'] ?? user['role'] ?? '');
    await prefs.setString('userPhone', phoneNumber);
    await prefs.setString('phoneNumber', phoneNumber);
    return user;
  }

  Future<void> signOut() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }

  Future<bool> isAuthenticated() async {
    final prefs = await SharedPreferences.getInstance();
    return (prefs.getBool('isAuthenticated') ?? false) && prefs.getString('authToken') != null;
  }

  Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('authToken');
  }

  Future<String?> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('userId');
  }

  Future<String?> getPhoneNumber() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('phoneNumber');
  }

  Future<Map<String, String?>> getUserInfo() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'userId': prefs.getString('userId'),
      'userName': prefs.getString('userName'),
      'userRole': prefs.getString('userRole'),
      'phoneNumber': prefs.getString('phoneNumber'),
    };
  }
}
