const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');

// Cargar el archivo proto
const PROTO_PATH = path.join(__dirname, '../user.proto');
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true
});

const userProto = grpc.loadPackageDefinition(packageDefinition).user;

// Crear cliente gRPC
const client = new userProto.UserService('localhost:50052', grpc.credentials.createInsecure());

// Variables globales para las pruebas
let testUserId = '';
let testToken = '';

// Función para ejecutar pruebas
async function runTests() {
    console.log('🧪 Iniciando pruebas del User Service...\n');

    try {
        // Test 1: Registro de usuario
        console.log(' Test 1: Registro de usuario');
        await testRegisterUser();

        // Test 2: Login de usuario
        console.log('\n Test 2: Login de usuario');
        await testLoginUser();

        // Test 3: Obtener información de usuario
        console.log('\n Test 3: Obtener información de usuario');
        await testGetUser();

        // Test 4: Actualizar usuario
        console.log('\n✏️ Test 4: Actualizar información de usuario');
        await testUpdateUser();

        // Test 5: Intentar registrar usuario duplicado
        console.log('\n Test 5: Intentar registrar usuario duplicado');
        await testDuplicateUser();

        // Test 6: Login con credenciales incorrectas
        console.log('\n🚫 Test 6: Login con credenciales incorrectas');
        await testInvalidLogin();

        // Test 7: Obtener usuario inexistente
        console.log('\n Test 7: Obtener usuario inexistente');
        await testGetNonexistentUser();

        // Test 8: Verificar token JWT
        console.log('\n Test 8: Verificar token JWT');
        await testVerifyToken();

        // Test 9: Eliminar usuario
        console.log('\n🗑️ Test 9: Eliminar usuario');
        await testDeleteUser();

        console.log('\n Todas las pruebas completadas!');

    } catch (error) {
        console.log(`\n Error en las pruebas: ${error.message}`);
    } finally {
        // Cerrar conexión
        client.close();
    }
}

// Test 1: Registro de usuario
function testRegisterUser() {
    return new Promise((resolve, reject) => {
        const request = {
            username: 'testuser123',
            password: 'password123'
        };

        client.RegisterUser(request, (error, response) => {
            if (error) {
                console.log(` Error: ${error.message}`);
                reject(error);
                return;
            }

            console.log(` Respuesta: ${response.status} - ${response.message}`);
            console.log(` Datos: ID=${response.user_id}, Usuario=${response.username}`);
            
            if (response.status === 'SUCCESS') {
                testUserId = response.user_id;
            }
            
            resolve(response);
        });
    });
}

// Test 2: Login de usuario
function testLoginUser() {
    return new Promise((resolve, reject) => {
        const request = {
            username: 'testuser123',
            password: 'password123'
        };

        client.LoginUser(request, (error, response) => {
            if (error) {
                console.log(` Error: ${error.message}`);
                reject(error);
                return;
            }

            console.log(` Respuesta: ${response.status} - ${response.message}`);
            console.log(` Datos: ID=${response.user_id}, Usuario=${response.username}, Token=${response.token ? 'Generado' : 'No generado'}`);
            
            if (response.status === 'SUCCESS') {
                testToken = response.token;
            }
            
            resolve(response);
        });
    });
}

// Test 3: Obtener información de usuario
function testGetUser() {
    return new Promise((resolve, reject) => {
        const request = {
            user_id: testUserId
        };

        client.GetUser(request, (error, response) => {
            if (error) {
                console.log(` Error: ${error.message}`);
                reject(error);
                return;
            }

            console.log(` Usuario encontrado:`);
            console.log(` Datos: ID=${response.user_id}, Usuario=${response.username}`);
            console.log(`📅 Creado: ${response.created_at}, Actualizado: ${response.updated_at}`);
            
            resolve(response);
        });
    });
}

// Test 4: Actualizar usuario
function testUpdateUser() {
    return new Promise((resolve, reject) => {
        const request = {
            user_id: testUserId,
            username: 'updateduser123'
        };

        client.UpdateUser(request, (error, response) => {
            if (error) {
                console.log(` Error: ${error.message}`);
                reject(error);
                return;
            }

            console.log(` Respuesta: ${response.status} - ${response.message}`);
            console.log(` Usuario actualizado: ${response.user_id}`);
            
            resolve(response);
        });
    });
}

// Test 5: Intentar registrar usuario duplicado
function testDuplicateUser() {
    return new Promise((resolve, reject) => {
        const request = {
            username: 'testuser123', // Mismo username que antes
            password: 'password456'
        };

        client.RegisterUser(request, (error, response) => {
            if (error) {
                console.log(` Error: ${error.message}`);
                reject(error);
                return;
            }

            console.log(` Respuesta esperada: ${response.status} - ${response.message}`);
            resolve(response);
        });
    });
}

// Test 6: Login con credenciales incorrectas
function testInvalidLogin() {
    return new Promise((resolve, reject) => {
        const request = {
            username: 'testuser123',
            password: 'wrongpassword'
        };

        client.LoginUser(request, (error, response) => {
            if (error) {
                console.log(` Error: ${error.message}`);
                reject(error);
                return;
            }

            console.log(` Respuesta esperada: ${response.status} - ${response.message}`);
            resolve(response);
        });
    });
}

// Test 7: Obtener usuario inexistente
function testGetNonexistentUser() {
    return new Promise((resolve, reject) => {
        const request = {
            user_id: 'nonexistent-user-id'
        };

        client.GetUser(request, (error, response) => {
            if (error) {
                console.log(` Error esperado: ${error.message}`);
                resolve(); // Error esperado
                return;
            }

            console.log(` No se esperaba respuesta exitosa`);
            resolve(response);
        });
    });
}

// Test 8: Verificar token JWT
function testVerifyToken() {
    return new Promise((resolve, reject) => {
        const request = {
            token: testToken
        };

        client.VerifyToken(request, (error, response) => {
            if (error) {
                console.log(` Error: ${error.message}`);
                reject(error);
                return;
            }

            console.log(` Respuesta: ${response.status} - ${response.message}`);
            console.log(` Token válido para: ID=${response.user_id}, Usuario=${response.username}`);
            console.log(` Token original: ${testToken.substring(0, 50)}...`);
            
            resolve(response);
        });
    });
}

// Test 9: Eliminar usuario
function testDeleteUser() {
    return new Promise((resolve, reject) => {
        const request = {
            user_id: testUserId
        };

        client.DeleteUser(request, (error, response) => {
            if (error) {
                console.log(` Error: ${error.message}`);
                reject(error);
                return;
            }

            console.log(` Respuesta: ${response.status} - ${response.message}`);
            resolve(response);
        });
    });
}

// Ejecutar las pruebas
runTests();
