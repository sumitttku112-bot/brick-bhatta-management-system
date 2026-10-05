import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/auth_service.dart';

final authServiceProvider = Provider<AuthService>((ref) => AuthService());

/// State is `true` when a user is logged in.
class AuthNotifier extends StateNotifier<AsyncValue<bool>> {
  final AuthService _authService;

  AuthNotifier(this._authService) : super(const AsyncValue.loading()) {
    _init();
  }

  Future<void> _init() async {
    try {
      state = AsyncValue.data(await _authService.isAuthenticated());
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }

  Future<void> login(String phoneNumber, String password) async {
    await _authService.login(phoneNumber, password);
    state = const AsyncValue.data(true);
  }

  Future<void> signOut() async {
    try {
      await _authService.signOut();
      state = const AsyncValue.data(false);
    } catch (e) {
      state = AsyncValue.error(e, StackTrace.current);
    }
  }
}

final authNotifierProvider = StateNotifierProvider<AuthNotifier, AsyncValue<bool>>((ref) {
  final authService = ref.watch(authServiceProvider);
  return AuthNotifier(authService);
});
