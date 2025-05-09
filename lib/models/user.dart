class User {
  final int? id;
  final String username;
  final String password;
  final String firstName;
  final String lastName;
  final String email;

  User({
    this.id,
    required this.username,
    required this.password,
    required this.firstName,
    required this.lastName,
    required this.email,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'username': username,
      'password': password,
      'firstName': firstName,
      'lastName': lastName,
      'email': email,
    };
  }

  factory User.fromMap(Map<String, dynamic> map) {
    return User(
      id: map['id'],
      username: map['username'],
      password: map['password'],
      firstName: map['firstName'],
      lastName: map['lastName'],
      email: map['email'],
    );
  }
}
