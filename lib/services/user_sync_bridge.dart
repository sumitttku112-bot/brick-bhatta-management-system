import 'package:hive/hive.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:convert';
import '../config/api_config.dart';
import '../models/user_model.dart';
import '../models/name_model.dart';
import '../data/user_data.dart';
import 'sync_service.dart';

class UserSyncBridge {
  /// Convert UserModel to NameModel for sync
  static NameModel userToName(UserModel user) {
    return NameModel(
      displayName: user.name,
      group: mapRoleToBackendGroup(user.role),
      phone: user.phoneNumber,
      gstin: user.gstNumber,
      commissionPercent: null, // Could be extracted from user data if available
      synced: false, // Will be determined by sync status
      createdAt: DateTime.now(),
    );
  }

  /// Convert NameModel to UserModel for compatibility
  static UserModel nameToUser(NameModel name) {
    return UserModel(
      id: name.serverId ?? name.createdAt.millisecondsSinceEpoch.toString(),
      name: name.displayName,
      nameHindi: name.displayName, // For now, same as display name
      role: name.group,
      roleHindi: _getRoleHindi(name.group),
      isActive: true,
      initials: _computeInitials(name.displayName),
      contactPerson: null,
      phoneNumber: name.phone,
      address: null,
      partyType: _getPartyType(name.group),
      gstNumber: name.gstin,
      openingBalance: null,
      openingBalanceType: null,
      creditLimit: null,
    );
  }

  /// Sync all users from UserData to the sync system
  static Future<void> syncUsersToNames() async {
    final users = UserData.getUsers();
    
    // Get current user phone to filter out (don't show self in ledger)
    final prefs = await SharedPreferences.getInstance();
    final currentUserPhone = prefs.getString('userPhone') ?? '';
    final currentUserRole = prefs.getString('userRole') ?? '';
    
    // Set for global usage (e.g. Reports, Add Party permissions)
    UserData.setCurrentUserPhone(currentUserPhone);
    UserData.setCurrentUserRole(currentUserRole);
    
    int syncedCount = 0;
    for (var user in users) {
      // Skip if phone matches current user
      // Also normalize phones for comparison to be safe
      final userPhone = (user.phoneNumber ?? '').replaceAll(' ', '');
      final currentPhone = currentUserPhone.replaceAll(' ', '');
      
      if (userPhone == currentPhone && currentPhone.isNotEmpty) {
        print('Skipping current user ${user.name} from ledger sync');
        continue;
      }

      final name = userToName(user);
      await SyncService.addName(name);
      syncedCount++;
    }
    
    print("🔄 Synced $syncedCount users to sync system (filtered self)");
  }

  /// Fetch all users from backend and populate local cache
  static Future<void> fetchAndSyncUsers() async {
    try {
      final headers = await ApiConfig.headers;
      
      final response = await http.get(
        Uri.parse(ApiConfig.usersUrl),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        final backendUsers = data.map((json) => UserModel.fromJson(json)).toList();
        
        // Clear local cache and repopulate
        UserData.clear();
        for (var user in backendUsers) {
          UserData.addUser(user);
        }
        print('✅ Fetched & Synced ${backendUsers.length} users from backend');
      } else {
        print('❌ Failed to fetch users: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ Error fetching users: $e');
    }
  }

  /// Get all users (from local cache)
  static List<UserModel> getAllUsers() {
    return UserData.getUsers();
  }

  /// Add a user to both UserData and sync system (OPTIMIZED)
  /// Add a user to backend and local storage.
  /// If [password] is given, the user can log in with it (set by an admin).
  static Future<void> addUser(UserModel user, {String? password}) async {
    try {
      print('🔄 UserSyncBridge: Adding user ${user.name}');
      
      // 1. Add to local cache first for responsiveness
      UserData.addUser(user);
      
      // 2. Send to Backend
      final headers = await ApiConfig.headers;
      print('🔑 [UserSyncBridge] Headers: ${headers.containsKey('Authorization') ? 'Authorization header present' : 'NO Authorization header'}');
      if (headers.containsKey('Authorization')) {
        final authHeader = headers['Authorization']!;
        print('🔑 [UserSyncBridge] Auth token: ${authHeader.substring(0, authHeader.length > 30 ? 30 : authHeader.length)}...');
      }
      
      final response = await http.post(
        Uri.parse(ApiConfig.usersUrl),
        headers: headers,
        body: jsonEncode({
          ...user.toJson(),
          if (password != null) 'password': password,
        }),
      );
        
      if (response.statusCode == 200 || response.statusCode == 201) {
        print('✅ UserSyncBridge: Added to Backend');
      } else if (password != null) {
        // Creating a login user must not fail silently
        UserData.removeUser(user.id);
        throw Exception('Failed to create user (${response.statusCode}): ${response.body}');
      } else {
        print('❌ UserSyncBridge: Failed to push to backend: ${response.statusCode}');
        print('❌ [UserSyncBridge] Response body: ${response.body}');
      }
      
    } catch (e) {
      print('❌ UserSyncBridge: Error adding user: $e');
      rethrow;
    }
  }

  /// Update a user
  static Future<void> updateUser(UserModel user) async {
    try {
      print('🔄 UserSyncBridge: Updating user ${user.name}');
      
      UserData.updateUser(user);
      
      // Send to Backend
      final headers = await ApiConfig.headers;
      final response = await http.put(
        Uri.parse(ApiConfig.getUserUrl(user.id)),
        headers: headers,
        body: jsonEncode(user.toJson()),
      );
        
        if (response.statusCode == 200) {
          print('✅ UserSyncBridge: Updated in Backend');
        } else {
          print('❌ UserSyncBridge: Failed to update backend: ${response.statusCode}');
        }
      
    } catch (e) {
      print('❌ UserSyncBridge: Error updating user: $e');
      rethrow;
    }
  }

  /// Remove a user from both UserData and sync system (OPTIMIZED)
  static Future<void> removeUser(String userId) async {
    try {
      print('🔄 UserSyncBridge: Removing user $userId');
      
      // Remove from existing UserData (fast local operation)
      UserData.removeUser(userId);
      print('✅ UserSyncBridge: Removed from UserData');
      
      // Optimized: Direct Hive box access for faster operations
      final box = await Hive.openBox<NameModel>('names');
      NameModel? matchingName;
      
      try {
        matchingName = box.values.firstWhere(
          (name) => name.serverId == userId || 
                    name.createdAt.millisecondsSinceEpoch.toString() == userId,
        );
        print('✅ UserSyncBridge: Found name to remove');
        
        // Direct delete without triggering full sync
        await matchingName.delete();
        print('✅ UserSyncBridge: Removed from sync system');
        
      } catch (e) {
        print('⚠️ UserSyncBridge: No matching name found in sync system: $e');
        // Continue anyway since the user was removed from UserData
      }
      
    } catch (e) {
      print('❌ UserSyncBridge: Error removing user: $e');
      rethrow;
    }
  }

  /// Clear all users from both systems
  static Future<void> clearAllUsers() async {
    UserData.clear();
    await SyncService.clearAllData();
  }

  /// Get sync status for users
  static Map<String, int> getSyncStatus() {
    return SyncService.getSyncStatus();
  }

  /// Force sync all pending changes (background operation)
  static Future<void> forceSync() async {
    try {
      print('🔄 UserSyncBridge: Starting background sync');
      await SyncService.syncNames();
      await SyncService.pullFromBackend();
      print('✅ UserSyncBridge: Background sync completed');
    } catch (e) {
      print('❌ UserSyncBridge: Background sync failed: $e');
      // Don't rethrow - background sync failures shouldn't crash the app
    }
  }

  // Helper methods
  
  /// Map app roles to backend-accepted group values
  /// Backend accepts: 'Labour', 'Thekedaar', 'Employee', 'General', 'Sale', 'Purchase'
  /// This is a public method so it can be used in other parts of the app
  static String mapRoleToBackendGroup(String role) {
    if (role.isEmpty) return 'General';
    
    final normalizedRole = role.toLowerCase().replaceAll(' ', '');
    
    switch (normalizedRole) {
      case 'admin':
      case 'pakkamuneem':
      case 'kacchamuneem':
      case 'employee':
      case 'manager':
      case 'muneem':
        // Map all staff/admin roles to 'Employee' for now
        // This keeps them separate from Labour/Sale/Purchase/General parties
        return 'Employee';
        
      case 'labour':
        return 'Labour';
      case 'thekedaar':
      case 'thekedar':
        return 'Thekedaar';
      case 'sale':
        return 'Sale';
      case 'purchase':
        return 'Purchase';
      case 'general':
        return 'General';
      default:
        // Default to 'General' for unknown roles
        return 'General';
    }
  }
  
  static String _getRoleHindi(String role) {
    switch (role.toLowerCase()) {
      case 'labour':
        return 'लेबर';
      case 'thekedaar':
        return 'ठेकेदार';
      case 'employee':
        return 'कर्मचारी';
      case 'sale':
        return 'बिक्री';
      case 'purchase':
        return 'खरीद';
      case 'general':
        return 'सामान्य';
      default:
        return role;
    }
  }

  static String _getPartyType(String group) {
    switch (group.toLowerCase()) {
      case 'labour':
      case 'thekedaar':
      case 'employee':
        return 'Customer';
      case 'sale':
      case 'purchase':
        return 'Supplier';
      default:
        return 'Customer';
    }
  }

  static String _computeInitials(String name) {
    final parts = name.trim().split(RegExp(r"\s+"));
    if (parts.isEmpty) return 'NA';
    if (parts.length == 1) return parts.first.substring(0, 1).toUpperCase();
    return (parts.first.substring(0, 1) + parts.last.substring(0, 1)).toUpperCase();
  }
}
