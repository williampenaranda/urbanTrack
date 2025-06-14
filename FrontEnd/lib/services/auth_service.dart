import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/user.dart';

class AuthService {
  static const String baseUrl = 'http://172.16.21.91:8000'; // Cambia IP

  Future<User> login(String username, String password) async {
    final url = Uri.parse('$baseUrl/api/auth/login');
    final payload = jsonEncode({
      'username': username,
      'password': password,
    });

    print('Enviando solicitud de login a $url');
    print('Payload: $payload');

    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: payload,
      );

      print('Respuesta del backend: ${response.statusCode} ${response.body}');

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        final userJson = responseData['user'];
        return User(
          id: userJson['id'],
          username: userJson['username'],
          password: password, // Opcional: tal vez no quieres almacenarlo
          first_name: userJson['first_name'],
          last_name: userJson['last_name'],
          email: userJson['email'],
        );
      } else {
        final errorResponse = jsonDecode(response.body);
        throw Exception(errorResponse['detail'] ?? 'No se pudo iniciar sesión');
      }
    } catch (e) {
      throw Exception('Error: ${e.toString()}');
    }
  }


  Future<String> register(User user) async {
    final url = Uri.parse('$baseUrl/api/auth/register');
    final payload = jsonEncode({
      'username': user.username,
      'password': user.password,
      'first_name': user.first_name,
      'last_name': user.last_name,
      'email': user.email,
    });

    print('Enviando solicitud de registro a $url');
    print('Payload: $payload');

    try {
      final response = await http.post(
        url,
        headers: {'Content-Type': 'application/json'},
        body: payload,
      );

      print('Respuesta del backend: ${response.statusCode} ${response.body}');

      if (response.statusCode == 201 || response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        return responseData['message'] ?? 'Registro exitoso';
      } else {
        final errorResponse = jsonDecode(response.body);
        return 'Error: ${errorResponse['detail'] ?? 'No se pudo registrar'}';
      }
    } catch (e) {
      return 'Error: ${e.toString()}';
    }
  }
  Future<String> updateUser(User user) async {
    final url = Uri.parse('$baseUrl/api/auth/users/${user.id}'); // Endpoint de actualización
    final payload = jsonEncode({
      'username': user.username,
      'first_name': user.first_name,
      'last_name': user.last_name,
      'email': user.email,
    });

    print('Enviando solicitud de actualización de usuario a $url');
    print('Payload: $payload');

    try {
      final response = await http.put(
        url,
        headers: {'Content-Type': 'application/json'},
        body: payload,
      );

      print('Respuesta del backend: ${response.statusCode} ${response.body}');

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        return responseData['message'] ?? 'Perfil actualizado exitosamente';
      } else {
        final errorResponse = jsonDecode(response.body);
        return 'Error: ${errorResponse['detail'] ?? 'No se pudo actualizar el perfil'}';
      }
    } catch (e) {
      return 'Error: ${e.toString()}';
    }
  }
}
  