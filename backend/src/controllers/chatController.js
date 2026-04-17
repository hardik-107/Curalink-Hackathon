const axios = require('axios');
const Chat = require('../models/Chat');

const processChatMessage = async (req, res) => {
    try {
        const { patientName, disease, intent, location, additionalQuery, mode, message } = req.body;

        // 1. Fetch past conversation history from MongoDB for this patient
        const pastChats = await Chat.find({ patientName }).sort({ createdAt: -1 }).limit(3);
        const history = pastChats.map(c => ({ 
            query: c.message || c.intent, 
            analysis: c.aiResponse 
        })).reverse();

        // 2. Prepare Payload for FastAPI (app.py)
        const combinedQuery = `${additionalQuery || ''} Follow-up: ${message || ''}`.trim();

        const pythonPayload = {
            patientName,
            disease,
            intent,
            location: location || "Global",
            additionalQuery: combinedQuery,
            mode: mode || "clinical",
            history
        };

        // --- DHYAN SE DEKH BHAI: ASLI FIX YAHAN HAI ---
        // Agar Render par PYTHON_API_URL set hai toh wo lega, nahi toh local (sirf dev ke liye)
        const PYTHON_URL = process.env.PYTHON_API_URL || "http://127.0.0.1:8000";
        
        console.log(`[INFO] Sending data to Python AI Engine at: ${PYTHON_URL}/generate for ${patientName}...`);

        // 3. Call the Python AI Engine with a massive 10-minute timeout
        const pythonResponse = await axios.post(`${PYTHON_URL}/generate`, pythonPayload, {
            timeout: 600000 // 10 minutes
        });

        const aiData = pythonResponse.data; // Expected: { analysis, sources, metadata }

        // 4. Save the successful run to MongoDB
        const newChat = new Chat({
            patientName,
            disease,
            intent,
            location,
            message,
            mode,
            aiResponse: aiData.analysis,
            sources: aiData.sources
        });
        await newChat.save();

        console.log(`[SUCCESS] Report generated and saved to DB for ${patientName}.`);

        // 5. Send data back to App.jsx
        res.status(200).json({ success: true, data: aiData });

    } catch (error) {
        console.error("[ERROR] Backend processing failed:", error.message);
        
        // Error handling for judges/users
        res.status(500).json({ 
            success: false, 
            message: "AI Engine is currently waking up or processing. Please wait 30 seconds and try again.",
            errorDetails: error.message 
        });
    }
};

module.exports = { processChatMessage };