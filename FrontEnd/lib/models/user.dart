class User {
  final int? id;
  final String username;
  final String password;
  final String first_name;
  final String last_name;
  final String email;

  User({
    this.id,
    required this.username,
    required this.password,
    required this.first_name,
    required this.last_name,
    required this.email,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'username': username,
      'password': password,
      'first_name': first_name,
      'lastame': last_name,
      'email': email,
    };
  }

  factory User.fromMap(Map<String, dynamic> map) {
    return User(
      id: map['id'],
      username: map['username'],
      password: map['password'] ?? "",
      first_name: map['first_name'],
      last_name: map['last_name'],
      email: map['email'],
    );
  }
}
