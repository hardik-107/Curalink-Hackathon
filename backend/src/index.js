const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const dotenv = require('dotenv');
const chatRoutes = require('./routes/chatRoutes');

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Routes
app.use('/api/chat', chatRoutes);

// MongoDB Connection (Fixed for Latest Mongoose Version)
mongoose.connect(process.env.MONGO_URI).then(() => {
    console.log("✅ MongoDB Connected successfully!");
    app.listen(PORT, () => {
        console.log(`🚀 Node Backend running on port ${PORT}`);
    });
}).catch((error) => {
    console.error("❌ MongoDB connection error:", error.message);
});