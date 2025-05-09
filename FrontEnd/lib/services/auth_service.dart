 import 'dart:convert'; 
import 'package:http/http.dart' as http; 
import '../models/user.dart'; 
 
class AuthService { 
  static const String baseUrl = "http://192.168.1.6:8000";
 
  Future<User> login(String username, String password) async { 
    final response = await http.post( 
      Uri.parse('$baseUrl/api/auth/login'), 
      headers: {'Content-Type': 'application/json'}, 
      body: jsonEncode({ 
        'username': username, 
        'password': password, 
      }), 
    ); 
 
    if (response.statusCode == 200) { 
      return User.fromMap(jsonDecode(response.body)['user']); 
    } else { 
      throw Exception('Error en el inicio de sesión'); 
    } 
  } 
 
  Future<User> register(User user) async { 
    final response = await http.post( 
      Uri.parse('$baseUrl/api/auth/register'), 
      headers: {'Content-Type': 'application/json'}, 
      body: jsonEncode(user.toMap()), 
    ); 
 
    if (response.statusCode == 201) { 
      return User.fromMap(jsonDecode(response.body)['user']); 
    } else { 
      throw Exception('Error en el registro'); 
    } 
} 
}