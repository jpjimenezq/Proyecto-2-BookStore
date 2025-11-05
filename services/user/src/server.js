require('dotenv').config();
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');
const path = require('path');
const { dbManager } = require('./db');
const UserServiceLogic = require('./services/user_service');

// Cargar el archivo proto desde contracts/proto
// __dirname es /app/src, entonces subimos a /app y luego a contracts/proto
const PROTO_PATH = path.join(__dirname, '..', 'contracts', 'proto', 'user.proto');
const PROTO_DIR = path.join(__dirname, '..', 'contracts', 'proto');
const packageDefinition = protoLoader.loadSync(PROTO_PATH, {
    keepCase: true,
    longs: String,
    enums: String,
    defaults: true,
    oneofs: true,
    includeDirs: [PROTO_DIR]
});

const userProto = grpc.loadPackageDefinition(packageDefinition).bookstore.user;

// Función para crear las "tablas" en MongoDB (inicializar índices)
async function createIndexes() {
    const maxRetries = 10;
    const retryDelay = 5000;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            console.log(`Creating indexes (attempt ${attempt})...`, { flush: true });
            
            const User = require('./models/user_model');
            
            // Crear índices únicos para optimizar las consultas
            await User.collection.createIndex({ user_id: 1 }, { unique: true });
            await User.collection.createIndex({ username: 1 }, { unique: true });
            
            console.log('Indexes created successfully', { flush: true });
            return true;
            
        } catch (error) {
            console.log(`Index creation error (attempt ${attempt}): ${error.message}`, { flush: true });
            
            if (attempt < maxRetries) {
                console.log(`[DB] Reintentando en ${retryDelay/1000} segundos...`, { flush: true });
                await new Promise(resolve => setTimeout(resolve, retryDelay));
            } else {
                console.log('[DB] No se pudieron crear los indices despues de todos los intentos', { flush: true });
                return false;
            }
        }
    }
    return false;
}

// Implementación del servicio gRPC
class UserService {
    constructor() {
        this.logic = new UserServiceLogic();
    }

    async RegisterUser(call, callback) {
        try {
            const result = await this.logic.registerUser({
                username: call.request.username,
                password: call.request.password,
                email: call.request.email || '',
                role: call.request.role || 'CLIENT'
            });

            if (result.success) {
                callback(null, {
                    user_id: result.user.user_id,
                    username: result.user.username,
                    email: result.user.email,
                    role: result.user.role,
                    status: 'SUCCESS',
                    message: result.message
                });
            } else {
                callback(null, {
                    user_id: '',
                    username: '',
                    email: '',
                    role: '',
                    status: 'ERROR',
                    message: result.message
                });
            }
        } catch (error) {
            console.log(`[RegisterUser] Error: ${error.message}`, { flush: true });
            callback(null, {
                user_id: '',
                username: '',
                email: '',
                role: '',
                status: 'ERROR',
                message: 'Error interno del servidor'
            });
        }
    }

    async LoginUser(call, callback) {
        try {
            const result = await this.logic.loginUser(
                call.request.username,
                call.request.password
            );

            if (result.success) {
                callback(null, {
                    user_id: result.user.user_id,
                    username: result.user.username,
                    email: result.user.email,
                    role: result.user.role,
                    token: result.token,
                    status: 'SUCCESS',
                    message: result.message
                });
            } else {
                callback(null, {
                    user_id: '',
                    username: '',
                    email: '',
                    role: '',
                    token: '',
                    status: 'ERROR',
                    message: result.message
                });
            }
        } catch (error) {
            console.log(`[LoginUser] Error: ${error.message}`, { flush: true });
            callback(null, {
                user_id: '',
                username: '',
                email: '',
                role: '',
                token: '',
                status: 'ERROR',
                message: 'Internal server error'
            });
        }
    }

    async GetUser(call, callback) {
        try {
            const result = await this.logic.getUser(call.request.user_id);

            if (result.success) {
                callback(null, {
                    user_id: result.user.user_id,
                    username: result.user.username,
                    email: result.user.email,
                    role: result.user.role,
                    created_at: result.user.created_at,
                    updated_at: result.user.updated_at
                });
            } else {
                const error = new Error(result.message);
                error.code = grpc.status.NOT_FOUND;
                callback(error);
            }
        } catch (error) {
            console.log(`[GetUser] Error: ${error.message}`, { flush: true });
            const grpcError = new Error('Error interno del servidor');
            grpcError.code = grpc.status.INTERNAL;
            callback(grpcError);
        }
    }

    async UpdateUser(call, callback) {
        try {
            const result = await this.logic.updateUser(call.request.user_id, {
                email: call.request.email,
                password: call.request.password
            });

            if (result.success) {
                callback(null, {
                    user_id: result.user.user_id,
                    username: result.user.username,
                    status: 'SUCCESS',
                    message: result.message
                });
            } else {
                callback(null, {
                    user_id: '',
                    username: '',
                    status: 'ERROR',
                    message: result.message
                });
            }
        } catch (error) {
            console.log(`[UpdateUser] Error: ${error.message}`, { flush: true });
            callback(null, {
                user_id: '',
                username: '',
                status: 'ERROR',
                message: 'Internal server error'
            });
        }
    }

    async DeleteUser(call, callback) {
        try {
            const result = await this.logic.deleteUser(call.request.user_id);

            if (result.success) {
                callback(null, {
                    status: 'SUCCESS',
                    message: result.message
                });
            } else {
                callback(null, {
                    status: 'ERROR',
                    message: result.message
                });
            }
        } catch (error) {
            console.log(`[DeleteUser] Error: ${error.message}`, { flush: true });
            callback(null, {
                status: 'ERROR',
                message: 'Error interno del servidor'
            });
        }
    }

    async VerifyToken(call, callback) {
        try {
            const result = this.logic.verifyToken(call.request.token);

            if (result.success) {
                callback(null, {
                    user_id: result.user.user_id,
                    username: result.user.username,
                    role: result.user.role || 'CLIENT',
                    status: 'SUCCESS',
                    message: 'Token válido'
                });
            } else {
                callback(null, {
                    user_id: '',
                    username: '',
                    role: '',
                    status: 'ERROR',
                    message: result.message
                });
            }
        } catch (error) {
            console.log(`[VerifyToken] Error: ${error.message}`, { flush: true });
            callback(null, {
                user_id: '',
                username: '',
                role: '',
                status: 'ERROR',
                message: 'Error interno del servidor'
            });
        }
    }
}

// Función principal para iniciar el servidor
async function main() {
    const dbConnected = await dbManager.connectWithRetry();
    if (!dbConnected) {
        console.log('Database connection failed', { flush: true });
        process.exit(1);
    }

    await createIndexes();

    const userService = new UserServiceLogic();
    await userService.initializeAdminUser();

    const server = new grpc.Server();
    server.addService(userProto.UserService.service, new UserService());

    const port = process.env.GRPC_PORT || '50054';
    const host = '0.0.0.0';
    
    server.bindAsync(
        `${host}:${port}`,
        grpc.ServerCredentials.createInsecure(),
        (error, port) => {
            if (error) {
                console.log(`Error starting server: ${error.message}`, { flush: true });
                return;
            }
            
            console.log(`User Service listening on ${host}:${port}`, { flush: true });
            server.start();
        }
    );

    process.on('SIGINT', async () => {
        server.tryShutdown((error) => {
            if (error) {
                console.log(`Shutdown error: ${error.message}`, { flush: true });
            }
        });
        
        await dbManager.disconnect();
        process.exit(0);
    });
}

// Iniciar servidor
main().catch(error => {
    console.log(`Error fatal: ${error.message}`, { flush: true });
    process.exit(1);
});