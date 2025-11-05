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

/**
 * Cliente para interactuar con el User Service desde otros microservicios
 * Ejemplo: Usar desde Order Service para validar usuarios
 */
class UserServiceClient {
    constructor(host = 'localhost:50052') {
        this.client = new userProto.UserService(host, grpc.credentials.createInsecure());
    }

    /**
     * Verificar si un token JWT es válido
     * @param {string} token - Token JWT a verificar
     * @returns {Promise} - Resultado de la verificación
     */
    async verifyToken(token) {
        return new Promise((resolve, reject) => {
            const request = { token };

            this.client.VerifyToken(request, (error, response) => {
                if (error) {
                    reject(error);
                    return;
                }

                if (response.status === 'SUCCESS') {
                    resolve({
                        valid: true,
                        user_id: response.user_id,
                        username: response.username,
                        message: response.message
                    });
                } else {
                    resolve({
                        valid: false,
                        message: response.message
                    });
                }
            });
        });
    }

    /**
     * Verificar si un usuario existe por ID
     * @param {string} userId - ID del usuario
     * @returns {Promise} - Información del usuario
     */
    async getUser(userId) {
        return new Promise((resolve, reject) => {
            const request = { user_id: userId };

            this.client.GetUser(request, (error, response) => {
                if (error) {
                    reject(error);
                    return;
                }

                resolve({
                    user_id: response.user_id,
                    username: response.username,
                    created_at: response.created_at,
                    updated_at: response.updated_at
                });
            });
        });
    }

    /**
     * Autenticar usuario con username y password
     * @param {string} username - Nombre de usuario
     * @param {string} password - Contraseña
     * @returns {Promise} - Token JWT y datos del usuario
     */
    async loginUser(username, password) {
        return new Promise((resolve, reject) => {
            const request = { username, password };

            this.client.LoginUser(request, (error, response) => {
                if (error) {
                    reject(error);
                    return;
                }

                if (response.status === 'SUCCESS') {
                    resolve({
                        success: true,
                        user_id: response.user_id,
                        username: response.username,
                        token: response.token,
                        message: response.message
                    });
                } else {
                    resolve({
                        success: false,
                        message: response.message
                    });
                }
            });
        });
    }

    /**
     * Cerrar la conexión
     */
    close() {
        this.client.close();
    }
}

// Ejemplo de uso en Order Service
async function exampleUsageInOrderService() {
    const userClient = new UserServiceClient();

    try {
        console.log('=== Ejemplo de uso del Token JWT en Order Service ===\n');

        // 1. Usuario se loguea y obtiene token
        console.log(' 1. Login de usuario...');
        const loginResult = await userClient.loginUser('testuser123', 'password123');
        
        if (loginResult.success) {
            console.log(` Login exitoso para: ${loginResult.username}`);
            console.log(`🎫 Token obtenido: ${loginResult.token.substring(0, 50)}...\n`);

            // 2. En Order Service: Verificar token antes de crear orden
            console.log('🛒 2. Crear orden - Verificando token...');
            const tokenVerification = await userClient.verifyToken(loginResult.token);
            
            if (tokenVerification.valid) {
                console.log(` Token válido para usuario: ${tokenVerification.username}`);
                console.log(` Procediendo a crear orden para user_id: ${tokenVerification.user_id}`);
                
                // Aquí llamarías al Order Service con el user_id validado
                console.log(' Llamada a Order Service seria aquí...\n');
                
                // 3. Verificar información completa del usuario
                console.log(' 3. Obteniendo información completa del usuario...');
                const userInfo = await userClient.getUser(tokenVerification.user_id);
                console.log(` Usuario: ${userInfo.username}, creado: ${userInfo.created_at}`);
                
            } else {
                console.log(` Token inválido: ${tokenVerification.message}`);
            }
            
        } else {
            console.log(` Login fallido: ${loginResult.message}`);
        }

    } catch (error) {
        console.log(` Error: ${error.message}`);
    } finally {
        userClient.close();
    }
}

// Exportar para uso en otros archivos
module.exports = UserServiceClient;

// Si se ejecuta directamente, mostrar ejemplo
if (require.main === module) {
    exampleUsageInOrderService();
}
