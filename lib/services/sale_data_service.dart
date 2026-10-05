import '../models/sale_model.dart';

import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/sale_model.dart';
import '../config/api_config.dart';

class SaleDataService {
  // Local cache
  static List<SaleEntry> _sales = [];

  static List<SaleEntry> getAllSales() {
    return List<SaleEntry>.unmodifiable(_sales);
  }

  /// Initialize: Fetch sales from backend
  static Future<void> fetchSales() async {
    try {
      final headers = await ApiConfig.headers;
      
      final response = await http.get(
        Uri.parse(ApiConfig.salesUrl),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _sales = data.map((json) => SaleEntry.fromJson(json)).toList();
        // Sort by date descending (newest first)
        _sales.sort((a, b) => b.date.compareTo(a.date));
        print('✅ Fetched ${_sales.length} sales from backend');
      } else {
        print('❌ Failed to fetch sales: ${response.statusCode}');
      }
    } catch (e) {
      print('❌ Error fetching sales: $e');
    }
  }

  static Future<bool> addSale(SaleEntry sale) async {
    try {
      final headers = await ApiConfig.headers;

      final response = await http.post(
        Uri.parse(ApiConfig.salesUrl),
        headers: headers,
        body: jsonEncode(sale.toJson()),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        final newSale = SaleEntry.fromJson(jsonDecode(response.body));
        _sales.insert(0, newSale);
        return true;
      } else {
        print('❌ Failed to add sale: ${response.statusCode} - ${response.body}');
        return false;
      }
    } catch (e) {
      print('❌ Error adding sale: $e');
      return false;
    }
  }

  static void updateSale(SaleEntry updatedSale) {
    // TODO: Implement backend update
    final index = _sales.indexWhere((s) => s.id == updatedSale.id);
    if (index != -1) {
      _sales[index] = updatedSale;
    }
  }

  static void deleteSale(String id) {
    // TODO: Implement backend delete
    _sales.removeWhere((s) => s.id == id);
  }

  static SaleEntry? getSaleById(String id) {
    try {
      return _sales.firstWhere((s) => s.id == id);
    } catch (e) {
      return null;
    }
  }

  static List<SaleEntry> getSalesByDateRange(DateTime start, DateTime end) {
    return _sales.where((sale) {
      return sale.date.isAfter(start.subtract(const Duration(days: 1))) &&
             sale.date.isBefore(end.add(const Duration(days: 1)));
    }).toList();
  }

  static void clearAll() {
    _sales.clear();
  }
}

