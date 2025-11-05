const User = require('../models/user_model');
const jwt = require('jsonwebtoken');

class UserServiceLogic {
    constructor() {
        this.jwtSecret = process.env.JWT_SECRET || 'your-secret-key-here';
        this.jwtExpire = process.env.JWT_EXPIRE || '24h';
    }

    // Registrar nuevo usuario
    async registerUser(userData) {
        try {
            const { username, password, email, role } = userData;

            // Verificar si el usuario ya existe
            const existingUser = await User.findOne({ username: username });

            if (existingUser) {
                throw new Error('USERNAME_EXISTS');
            }

            // Si se proporciona email, verificar que no exista
            if (email) {
                const existingEmail = await User.findOne({ email: email });
                if (existingEmail) {
                    throw new Error('EMAIL_EXISTS');
                }
            }

            // Crear nuevo usuario
            const newUser = new User({
                username,
                password,
                email: email || undefined,
                role: role || 'CLIENT'
            });

            const savedUser = await newUser.save();

            return {
                success: true,
                user: savedUser.toPublicJSON(),
                message: 'Usuario registrado exitosamente'
            };

        } catch (error) {
            console.log(`[UserService] Error en registerUser: ${error.message}`);
            return {
                success: false,
                error: error.message,
                message: this.getErrorMessage(error.message)
            };
        }
    }

    // Iniciar sesión
    async loginUser(username, password) {
        try {
            // Buscar usuario por username o email
            const user = await User.findOne({
                $or: [
                    { username: username },
                    { email: username }
                ]
            });

            if (!user) {
                throw new Error('USER_NOT_FOUND');
            }

            // Verificar que el usuario esté activo
            if (user.status !== 'ACTIVE') {
                throw new Error('USER_INACTIVE');
            }

            // Verificar contraseña
            const isPasswordValid = await user.comparePassword(password);
            if (!isPasswordValid) {
                throw new Error('INVALID_PASSWORD');
            }

            // Generar token JWT
            const token = jwt.sign(
                { 
                    user_id: user.user_id,
                    username: user.username,
                    email: user.email || '',
                    role: user.role
                },
                this.jwtSecret,
                { expiresIn: this.jwtExpire }
            );

            return {
                success: true,
                user: user.toPublicJSON(),
                token: token,
                message: 'Login exitoso'
            };

        } catch (error) {
            console.log(`[UserService] Error en loginUser: ${error.message}`);
            return {
                success: false,
                error: error.message,
                message: this.getErrorMessage(error.message)
            };
        }
    }

    // Obtener usuario por ID
    async getUser(userId) {
        try {
            const user = await User.findOne({ user_id: userId });

            if (!user) {
                throw new Error('USER_NOT_FOUND');
            }

            return {
                success: true,
                user: user.toPublicJSON()
            };

        } catch (error) {
            console.log(`[UserService] Error en getUser: ${error.message}`);
            return {
                success: false,
                error: error.message,
                message: this.getErrorMessage(error.message)
            };
        }
    }

    // Actualizar usuario
    async updateUser(userId, updateData) {
        try {
            const { username } = updateData;

            // Verificar si el usuario existe
            const existingUser = await User.findOne({ user_id: userId });
            if (!existingUser) {
                throw new Error('USER_NOT_FOUND');
            }

            // Si se está actualizando el username, verificar que no exista otro usuario con ese username
            if (username && username !== existingUser.username) {
                const usernameExists = await User.findOne({ 
                    username: username,
                    user_id: { $ne: userId }
                });
                if (usernameExists) {
                    throw new Error('USERNAME_EXISTS');
                }
            }

            // Actualizar usuario
            const updatedUser = await User.findOneAndUpdate(
                { user_id: userId },
                {
                    ...(username && { username }),
                    updated_at: new Date()
                },
                { new: true }
            );

            return {
                success: true,
                user: updatedUser.toPublicJSON(),
                message: 'Usuario actualizado exitosamente'
            };

        } catch (error) {
            console.log(`[UserService] Error en updateUser: ${error.message}`);
            return {
                success: false,
                error: error.message,
                message: this.getErrorMessage(error.message)
            };
        }
    }

    // Eliminar usuario
    async deleteUser(userId) {
        try {
            const user = await User.findOne({ user_id: userId });
            if (!user) {
                throw new Error('USER_NOT_FOUND');
            }

            await User.findOneAndDelete({ user_id: userId });

            return {
                success: true,
                message: 'Usuario eliminado exitosamente'
            };

        } catch (error) {
            console.log(`[UserService] Error en deleteUser: ${error.message}`);
            return {
                success: false,
                error: error.message,
                message: this.getErrorMessage(error.message)
            };
        }
    }

    // Verificar token JWT
    verifyToken(token) {
        try {
            const decoded = jwt.verify(token, this.jwtSecret);
            return {
                success: true,
                user: decoded
            };
        } catch (error) {
            return {
                success: false,
                error: 'INVALID_TOKEN',
                message: 'Token inválido o expirado'
            };
        }
    }

    // Obtener mensaje de error en español
    getErrorMessage(errorCode) {
        const errorMessages = {
            'USERNAME_EXISTS': 'El nombre de usuario ya existe',
            'EMAIL_EXISTS': 'El correo electrónico ya existe',
            'USER_NOT_FOUND': 'Usuario no encontrado',
            'USER_INACTIVE': 'Usuario inactivo',
            'INVALID_PASSWORD': 'Contraseña incorrecta',
            'INVALID_TOKEN': 'Token inválido o expirado'
        };

        return errorMessages[errorCode] || 'Error interno del servidor';
    }

    // Inicializar usuario admin si no existe
    async initializeAdminUser() {
        try {
            const adminEmail = 'admin@admin.com';
            const existingAdmin = await User.findOne({ email: adminEmail });

            if (!existingAdmin) {
                const adminUser = new User({
                    username: 'admin',
                    email: adminEmail,
                    password: 'Admin123',
                    role: 'ADMIN',
                    status: 'ACTIVE'
                });

                await adminUser.save();
                console.log('Admin user initialized');
            }
        } catch (error) {
            console.log(`Error initializing admin user: ${error.message}`);
        }
    }
}

module.exports = UserServiceLogic;
