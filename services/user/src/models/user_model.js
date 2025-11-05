const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');

// Esquema del usuario simplificado
const userSchema = new mongoose.Schema({
    user_id: {
        type: String,
        default: uuidv4,
        unique: true,
        required: true
    },
    username: {
        type: String,
        required: true,
        unique: true,
        trim: true,
        minlength: 3,
        maxlength: 30
    },
    email: {
        type: String,
        required: false,
        unique: true,
        sparse: true,
        trim: true,
        lowercase: true
    },
    password: {
        type: String,
        required: true,
        minlength: 6
    },
    role: {
        type: String,
        enum: ['ADMIN', 'CLIENT'],
        default: 'CLIENT'
    },
    status: {
        type: String,
        enum: ['ACTIVE', 'INACTIVE'],
        default: 'ACTIVE'
    },
    created_at: {
        type: Date,
        default: Date.now
    },
    updated_at: {
        type: Date,
        default: Date.now
    }
});

// Middleware para hashear la contraseña antes de guardar
userSchema.pre('save', async function(next) {
    const user = this;
    
    // Solo hashear la contraseña si ha sido modificada (o es nueva)
    if (!user.isModified('password')) return next();
    
    try {
        // Generar salt y hashear la contraseña
        const salt = await bcrypt.genSalt(10);
        const hashedPassword = await bcrypt.hash(user.password, salt);
        user.password = hashedPassword;
        
        // Actualizar fecha de modificación
        user.updated_at = new Date();
        
        next();
    } catch (error) {
        next(error);
    }
});

// Middleware para actualizar la fecha cuando se modifica el documento
userSchema.pre('findOneAndUpdate', function(next) {
    this.set({ updated_at: new Date() });
    next();
});

// Método para comparar contraseñas
userSchema.methods.comparePassword = async function(candidatePassword) {
    try {
        return await bcrypt.compare(candidatePassword, this.password);
    } catch (error) {
        throw error;
    }
};

// Método para obtener información pública del usuario (sin contraseña)
userSchema.methods.toPublicJSON = function() {
    return {
        user_id: this.user_id,
        username: this.username,
        email: this.email || '',
        role: this.role,
        status: this.status,
        created_at: this.created_at.toISOString(),
        updated_at: this.updated_at.toISOString()
    };
};

// Crear el modelo
const User = mongoose.model('User', userSchema);

module.exports = User;
