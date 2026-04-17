const mongoose = require('mongoose');

const chatSchema = new mongoose.Schema({
    patientName: { type: String, required: true },
    disease: { type: String, required: true },
    intent: { type: String, required: true },
    location: { type: String },
    message: { type: String }, // The follow-up question
    mode: { type: String, default: 'clinical' },
    aiResponse: { type: String }, // The final markdown report
    sources: { type: Array, default: [] } // Saved papers/trials
}, { timestamps: true });

module.exports = mongoose.model('Chat', chatSchema);