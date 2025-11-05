const mongoose = require('mongoose');

class DatabaseManager {
    constructor() {
        this.isConnected = false;
    }

    async connectWithRetry(maxRetries = 10, retryDelay = 5000) {
        const mongoUrl = process.env.MONGODB_URI || process.env.MONGO_URI || process.env.MONGO_URL || 'mongodb://mongo-user:27017/userdb';
        
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                console.log(`Database connection attempt ${attempt}...`);
                
                await mongoose.connect(mongoUrl, {
                    useNewUrlParser: true,
                    useUnifiedTopology: true,
                });

                this.isConnected = true;
                console.log('Connected to MongoDB');
                return true;

            } catch (error) {
                console.log(`Connection error (attempt ${attempt}): ${error.message}`);
                
                if (attempt < maxRetries) {
                    console.log(`[DB] Reintentando en ${retryDelay/1000} segundos...`);
                    await new Promise(resolve => setTimeout(resolve, retryDelay));
                } else {
                    console.log('[DB] No se pudo conectar a MongoDB despues de todos los intentos');
                    return false;
                }
            }
        }
        return false;
    }

    async disconnect() {
        try {
            await mongoose.disconnect();
            this.isConnected = false;
            console.log('[DB] Desconectado de MongoDB');
        } catch (error) {
            console.log(`[DB] Error al desconectar: ${error.message}`);
        }
    }

    getConnectionStatus() {
        return {
            isConnected: this.isConnected,
            readyState: mongoose.connection.readyState,
            name: mongoose.connection.name,
            host: mongoose.connection.host,
            port: mongoose.connection.port
        };
    }
}

// Eventos de conexión
mongoose.connection.on('connected', () => {
    console.log('[DB] Mongoose conectado a MongoDB');
});

mongoose.connection.on('error', (err) => {
    console.log(`[DB] Error de conexión Mongoose: ${err}`);
});

mongoose.connection.on('disconnected', () => {
    console.log('[DB] Mongoose desconectado');
});

// Manejar cierre de la aplicación
process.on('SIGINT', async () => {
    await mongoose.connection.close();
    console.log('[DB] Conexión MongoDB cerrada por terminación de la aplicación');
    process.exit(0);
});

const dbManager = new DatabaseManager();

module.exports = {
    dbManager,
    mongoose
};