import 'package:flutter/material.dart';
import '../models/user.dart';
import '../services/auth_service.dart';

class PerfilScreen extends StatefulWidget {
  final User user;
  const PerfilScreen({Key? key, required this.user}) : super(key: key);

  @override
  State<PerfilScreen> createState() => _PerfilScreenState();
}

class _PerfilScreenState extends State<PerfilScreen> {
  final _formKey = GlobalKey<FormState>();
  late TextEditingController _usernameController;
  late TextEditingController _firstNameController;
  late TextEditingController _lastNameController;
  late TextEditingController _emailController;
  bool _isEditing = false;
  late User _originalUser;

  @override
  void initState() {
    super.initState();
    _originalUser = widget.user;
    _usernameController = TextEditingController(text: _originalUser.username);
    _firstNameController = TextEditingController(text: _originalUser.first_name);
    _lastNameController = TextEditingController(text: _originalUser.last_name);
    _emailController = TextEditingController(text: _originalUser.email);
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _firstNameController.dispose();
    _lastNameController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  void _saveProfile() async {
    if (_formKey.currentState!.validate()) {
      // Actualiza el usuario con los nuevos datos
      User updatedUser = User(
        id: _originalUser.id,
        username: _usernameController.text,
        password: _originalUser.password, // password no cambia
        first_name: _firstNameController.text,
        last_name: _lastNameController.text,
        email: _emailController.text,
      );

      // Enviar la solicitud al backend
      try {
        final responseMessage = await AuthService().updateUser(updatedUser);
        final isError = responseMessage.startsWith('Error');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(responseMessage),
            backgroundColor: isError ? Colors.red : Colors.green,
          ),
        );
        if (!isError) {
          setState(() {
            _originalUser = updatedUser;
            _isEditing = false;
          });
        }
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error: ${e.toString()}'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  void _restoreProfile() {
    setState(() {
      _usernameController.text = _originalUser.username;
      _firstNameController.text = _originalUser.first_name;
      _lastNameController.text = _originalUser.last_name;
      _emailController.text = _originalUser.email;
      _isEditing = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SingleChildScrollView(
        child: Column(
          children: [
            // Header with avatar
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.indigo,
                borderRadius: const BorderRadius.only(
                  bottomLeft: Radius.circular(30),
                  bottomRight: Radius.circular(30),
                ),
              ),
              child: SafeArea(
                child: Column(
                  children: [
                    const CircleAvatar(
                      radius: 50,
                      backgroundColor: Colors.white,
                      child: Icon(
                        Icons.person,
                        size: 50,
                        color: Colors.indigo,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Text(
                      _usernameController.text,
                      style: const TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    Text(
                      _emailController.text,
                      style: const TextStyle(
                        color: Colors.white70,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // Profile form
            Padding(
              padding: const EdgeInsets.all(16),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _buildTextField(_usernameController, 'Nombre de Usuario', Icons.person_outline),
                    const SizedBox(height: 16),
                    _buildTextField(_firstNameController, 'Nombre', Icons.badge),
                    const SizedBox(height: 16),
                    _buildTextField(_lastNameController, 'Apellido', Icons.badge_outlined),
                    const SizedBox(height: 16),
                    _buildTextField(_emailController, 'Email', Icons.email),
                    const SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: () {
                        if (_isEditing) {
                          _saveProfile();
                        } else {
                          setState(() => _isEditing = true);
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: _isEditing ? Colors.green : Colors.indigo,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: Text(_isEditing ? 'Guardar Cambios' : 'Editar Perfil'),
                    ),
                    const SizedBox(height: 16),
                    if (_isEditing)
                      TextButton(
                        onPressed: _restoreProfile,
                        child: const Text('Cancelar'),
                      ),
                    const SizedBox(height: 16),
                    OutlinedButton(
                      onPressed: () {
                        Navigator.of(context).pushReplacementNamed('api/auth/login');
                      },
                      style: OutlinedButton.styleFrom(
                        foregroundColor: Colors.red,
                        side: const BorderSide(color: Colors.red),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: const Text('Cerrar Sesión'),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTextField(TextEditingController controller, String label, IconData icon) {
    bool isEmail = label.toLowerCase() == 'email';
    return TextFormField(
      controller: controller,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon),
      ),
      enabled: _isEditing,
      validator: (value) {
        if (value == null || value.isEmpty) {
          return 'Por favor ingrese su $label';
        }
        if (isEmail && !value.contains('@')) {
          return 'Por favor ingrese un email válido';
        }
        return null;
      },
    );
  }
}
