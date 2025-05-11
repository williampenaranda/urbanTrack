import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'map_screen.dart';
import 'rutas_screen.dart';
import 'perfil_screen.dart';

class HomePage extends StatefulWidget {
  const HomePage({Key? key}) : super(key: key);

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _selectedIndex = 0;
  final TextEditingController _locationController = TextEditingController();
  final PageController _pageController = PageController();

  final _screens = [
    MapScreen(),
    RutasScreen(),
    PerfilScreen(),
  ];

  // Lista de ejemplo de buses
  final List<Map<String, dynamic>> _proximosBuses = [
    {
      'numero': 'B101',
      'ruta': 'Terminal - Centro',
      'tiempo': '5 min',
      'distancia': '0.5 km'
    },
    {
      'numero': 'B205',
      'ruta': 'Bocagrande - Bazurto',
      'tiempo': '8 min',
      'distancia': '1.2 km'
    },
    {
      'numero': 'B308',
      'ruta': 'Transcaribe T102',
      'tiempo': '12 min',
      'distancia': '2.0 km'
    },
  ];

  void _onItemTapped(int index) {
    setState(() {
      _selectedIndex = index;
      _pageController.animateToPage(
        index,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    });
  }

  Future<void> _getCurrentLocation() async {
    try {
      // Verificar permisos de ubicación
      LocationPermission permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
        if (permission == LocationPermission.denied) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Permisos de ubicación denegados')),
          );
          return;
        }
      }

      if (permission == LocationPermission.deniedForever) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
                'Los permisos de ubicación están permanentemente denegados'),
            action: SnackBarAction(
              label: 'CONFIGURACIÓN',
              onPressed: () => Geolocator.openAppSettings(),
            ),
          ),
        );
        return;
      }

      // Obtener la ubicación actual
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Obteniendo ubicación...')),
      );

      Position position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      setState(() {
        _locationController.text =
            '${position.latitude.toStringAsFixed(4)}, ${position.longitude.toStringAsFixed(4)}';
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error al obtener la ubicación: $e')),
      );
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Asistente de Transporte',
          style: TextStyle(fontWeight: FontWeight.bold),
        ),
        backgroundColor: Colors.indigo,
        elevation: 0,
      ),
      body: PageView(
        controller: _pageController,
        onPageChanged: (index) {
          setState(() => _selectedIndex = index);
        },
        children: [
          Column(
            children: [
              // Barra de búsqueda y botón de ubicación
              Container(
                padding: EdgeInsets.all(16),
                color: Colors.indigo.withOpacity(0.1),
                child: Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _locationController,
                        decoration: InputDecoration(
                          hintText: 'Ingresa tu ubicación',
                          prefixIcon: Icon(Icons.search),
                          border: OutlineInputBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          filled: true,
                          fillColor: Colors.white,
                        ),
                      ),
                    ),
                    SizedBox(width: 8),
                    IconButton(
                      onPressed: _getCurrentLocation,
                      icon: Icon(Icons.my_location),
                      color: Colors.indigo,
                      tooltip: 'Usar ubicación actual',
                    ),
                  ],
                ),
              ),
              // Sección del mapa
              Expanded(
                flex: 2, // Ocupa 2/3 del espacio disponible
                child: Container(
                  color: Colors.grey[200],
                  child: MapScreen(),
                ),
              ),
              // Lista de próximos buses en un contenedor scrollable
              Container(
                height: 200, // Altura fija para la lista de buses
                decoration: BoxDecoration(
                  color: Colors.white,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.grey.withOpacity(0.3),
                      spreadRadius: 1,
                      blurRadius: 5,
                      offset: Offset(0, -2),
                    ),
                  ],
                ),
                child: Column(
                  children: [
                    Padding(
                      padding: EdgeInsets.all(8.0),
                      child: Row(
                        children: [
                          Icon(Icons.directions_bus, color: Colors.indigo),
                          SizedBox(width: 8),
                          Text(
                            'Buses próximos a llegar',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(
                      child: ListView.builder(
                        itemCount: _proximosBuses.length,
                        padding: EdgeInsets.symmetric(horizontal: 8),
                        itemBuilder: (context, index) {
                          final bus = _proximosBuses[index];
                          return Card(
                            elevation: 2,
                            margin: EdgeInsets.symmetric(vertical: 4),
                            child: ListTile(
                              leading: CircleAvatar(
                                backgroundColor: Colors.indigo,
                                child: Text(
                                  bus['numero'].substring(1),
                                  style: TextStyle(color: Colors.white),
                                ),
                              ),
                              title: Text(
                                bus['ruta'],
                                style: TextStyle(fontWeight: FontWeight.bold),
                              ),
                              subtitle: Text('Llegada en ${bus['tiempo']}'),
                              trailing: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Text(
                                    bus['distancia'],
                                    style: TextStyle(
                                      color: Colors.grey[600],
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          RutasScreen(),
          PerfilScreen(),
        ],
      ),
      floatingActionButton: _selectedIndex == 0
          ? FloatingActionButton.extended(
              onPressed: () {
                // Variables para el formulario
                final _formKey = GlobalKey<FormState>();
                final _routeController = TextEditingController();
                final _locationController = TextEditingController();
                final _descriptionController = TextEditingController();

                showDialog(
                  context: context,
                  builder: (BuildContext context) {
                    return AlertDialog(
                      title: const Text('Reportar Irregularidad'),
                      content: Form(
                        key: _formKey,
                        child: SingleChildScrollView(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              TextFormField(
                                controller: _routeController,
                                decoration: const InputDecoration(
                                  labelText: 'Ruta',
                                  hintText: 'Ej: T102, X104',
                                  prefixIcon: Icon(Icons.directions_bus),
                                ),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Por favor ingrese la ruta';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 16),
                              TextFormField(
                                controller: _locationController,
                                decoration: const InputDecoration(
                                  labelText: 'Ubicación',
                                  hintText: 'Ej: Estación Madre Bernarda',
                                  prefixIcon: Icon(Icons.location_on),
                                ),
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Por favor ingrese la ubicación';
                                  }
                                  return null;
                                },
                              ),
                              const SizedBox(height: 16),
                              TextFormField(
                                controller: _descriptionController,
                                decoration: const InputDecoration(
                                  labelText: 'Descripción',
                                  hintText: 'Describa la irregularidad',
                                  prefixIcon: Icon(Icons.description),
                                ),
                                maxLines: 3,
                                validator: (value) {
                                  if (value == null || value.isEmpty) {
                                    return 'Por favor describa la irregularidad';
                                  }
                                  return null;
                                },
                              ),
                            ],
                          ),
                        ),
                      ),
                      actions: [
                        TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text('Cancelar'),
                        ),
                        ElevatedButton(
                          onPressed: () {
                            if (_formKey.currentState!.validate()) {
                              // Aquí iría la lógica para enviar el reporte
                              Navigator.pop(context);
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content:
                                      Text('Reporte enviado correctamente'),
                                  backgroundColor: Colors.green,
                                ),
                              );
                            }
                          },
                          child: const Text('Enviar Reporte'),
                        ),
                      ],
                    );
                  },
                );
              },
              icon: const Icon(Icons.warning, color: Colors.white),
              label: const Text('Reportar'),
              backgroundColor: Colors.redAccent,
              tooltip: 'Reportar irregularidad',
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: _onItemTapped,
        backgroundColor: Colors.white,
        elevation: 8,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.map),
            label: 'Mapa',
          ),
          NavigationDestination(
            icon: Icon(Icons.route),
            label: 'Rutas',
          ),
          NavigationDestination(
            icon: Icon(Icons.person),
            label: 'Perfil',
          ),
        ],
      ),
    );
  }
}
