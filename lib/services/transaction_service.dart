import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/transaction_model.dart';

class TransactionService {
  static List<TransactionItem> _transactions = [];

  // Get all transactions from local cache
  static List<TransactionItem> getAllTransactions() {
    return List.from(_transactions);
  }

  // Fetch from backend
  static Future<List<TransactionItem>> fetchTransactions() async {
    try {
      final headers = await ApiConfig.headers;

      final response = await http.get(
        Uri.parse(ApiConfig.transactionsUrl),
        headers: headers,
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _transactions = data.map((json) => TransactionItem.fromJson(json)).toList();
        print('✅ Fetched ${_transactions.length} transactions');
        return _transactions;
      } else {
        print('❌ Failed to fetch transactions: ${response.statusCode}');
        return [];
      }
    } catch (e) {
      print('❌ Error fetching transactions: $e');
      return [];
    }
  }

  // Add new
  static Future<TransactionItem?> addTransaction(TransactionItem txn) async {
    try {
      final headers = await ApiConfig.headers;

      final response = await http.post(
        Uri.parse(ApiConfig.transactionsUrl),
        headers: headers,
        body: jsonEncode(txn.toJson()),
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        print('✅ Transaction added to backend');
        // Parse the response to get the created transaction with server ID
        final responseData = jsonDecode(response.body);
        final createdTransaction = TransactionItem.fromJson(responseData);
        
        // Check if transaction already exists (avoid duplicates)
        final exists = _transactions.any((t) => 
          t.id == createdTransaction.id || 
          (t.id == null && t.date == createdTransaction.date && 
           t.amount == createdTransaction.amount && 
           t.englishName == createdTransaction.englishName)
        );
        
        if (!exists) {
          _transactions.insert(0, createdTransaction);
        }
        
        return createdTransaction;
      } else {
         print('❌ Failed to add transaction: ${response.statusCode} - ${response.body}');
         return null;
      }
    } catch (e) {
      print('❌ Error adding transaction: $e');
      return null;
    }
  }
}
