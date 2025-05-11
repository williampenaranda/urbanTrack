 import 'dart:convert'; 
import 'package:http/http.dart' as http; 
import '../models/user.dart'; 
 
class AuthService { 
  static const String baseUrl = "http://192.168.1.6:8000";
 
  Future<User> login(String username, String password) async {
    // Construimos el payload con los datos de autenticación.
    final Map<String, String> payload = {
      'username': username,
      'password': password,
    };

    // Imprime el payload enviado para depurar.
    print("Login - Payload enviado: ${jsonEncode(payload)}");

    final response = await http.post(
      Uri.parse('$baseUrl/api/auth/login'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    // Imprime el código de respuesta y el cuerpo recibido.
    print("Login - Código de respuesta: ${response.statusCode}");
    print("Login - Respuesta del servidor: ${response.body}");

    if (response.statusCode == 200) {
      final Map<String, dynamic> jsonResult = jsonDecode(response.body);
      final Map<String, dynamic> userData = jsonResult["user"];
      print("Datos recibidos para user: $userData");
      return User.fromMap(jsonDecode(response.body)['user']);
    } else {
      throw Exception('Error en el inicio de sesión');
    }
  }

    Future<String> register(User user) async {
    // Construir un payload con las claves que espera el backend.
    final Map<String, dynamic> payload = {
      'username': user.username,
      'password': user.password,
      'first_name': user.first_name, // Conversión de camelCase a snake_case.
      'last_name': user.last_name,
      'email': user.email,
    };

    // Imprime el payload enviado para depuración.
    print("Register - Payload enviado: ${jsonEncode(payload)}");

    final response = await http.post(
      Uri.parse('$baseUrl/api/auth/register'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    // Imprime el código de respuesta y el contenido de la respuesta.
    print("Register - Código de respuesta: ${response.statusCode}");
    print("Register - Respuesta del servidor: ${response.body}");

    if (response.statusCode == 201) {
      final Map<String, dynamic> result = jsonDecode(response.body);
      // Se espera que el backend retorne {"message": "Usuario registrado exitosamente"}
      if(result.containsKey('message')){
        return result['message'];
      } else {
        throw Exception("Respuesta inesperada: ${response.body}");
      }
    } else {
      throw Exception('Usuario Registrado Correctamente');
    }
  }
}