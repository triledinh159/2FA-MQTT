const express = require('express');
const crypto = require('crypto');
const AWS = require('aws-sdk');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');
const { Parser } = require('json2csv'); // Library to convert JSON to CSV
require('dotenv').config(); // Load environment variables from .env file

const app = express();
app.use(express.json());
app.use(express.static('public')); // Serve static files from the 'public' directory

// Load environment variables from .env file
const {
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
    DYNAMODB_TABLE
} = process.env;

// Configure AWS DynamoDB
AWS.config.update({
    accessKeyId: AWS_ACCESS_KEY_ID,
    secretAccessKey: AWS_SECRET_ACCESS_KEY,
    region: AWS_REGION
});

const dynamoDb = new AWS.DynamoDB.DocumentClient();

// Function to generate random string
function generateRandomString(length) {
    return crypto.randomBytes(length).toString('hex');
}

// Function to encrypt data using AES-128-CBC
function encryptData(data, key, iv) {
    const cipher = crypto.createCipheriv('aes-128-cbc', key, iv);
    let encrypted = cipher.update(data, 'utf8', 'hex');
    encrypted += cipher.final('hex');
    return encrypted;
}

// Route to handle registration
app.post('/register', async (req, res) => {
    const { email } = req.body;

    if (!email) {
        return res.status(400).json({ error: 'Email is required' });
    }

    const username = generateRandomString(8);
    const password = generateRandomString(12);
    const aesKey = crypto.randomBytes(16); // AES-128 key is 16 bytes
    const iv = crypto.randomBytes(16);
    const OTP = 0;
    const EXPIRATION_TIME = 0;
    const encryptedUsername = encryptData(username, aesKey, iv);
    const encryptedPassword = encryptData(password, aesKey, iv);

    // Store username and password in a JSON file
    const userData = {
        user_id: username,
        password_hash: crypto.createHash('sha256').update(password).digest('hex'),
        is_superuser: false
    };

    const filePath = path.join(__dirname, 'user', `${email}.json`);
    fs.writeFileSync(filePath, JSON.stringify([userData], null, 4));

    // Insert into DynamoDB
    const params = {
        TableName: DYNAMODB_TABLE,
        Item: {
            email,
            OTP,
            EXPIRATION_TIME,
            Username: encryptedUsername,
            Password: encryptedPassword
        }
    };

    try {
        await dynamoDb.put(params).promise();

        // Execute the first curl command to get the token
        const loginCommand = `curl -X 'POST' 'http://localhost:18083/api/v5/login' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{"username": "<EMQX_usr>", "password": "<EMQX_passwd>"}'`;
        exec(loginCommand, (loginError, loginStdout, loginStderr) => {
            if (loginError) {
                console.error(`Login exec error: ${loginError}`);
                return res.status(500).json({ error: 'Could not obtain token' });
            }

            try {
                const loginResponse = JSON.parse(loginStdout);
                const token = loginResponse.token;

                // Execute the second curl command with the token
                const importCommand = `curl -v -u <EMQX_usr>:<EMQX_passwd> -X 'POST' -H 'Content-Type: multipart/form-data' -H 'Authorization: Bearer ${token}' -F 'filename=@${filePath}' 'http://localhost:18083/api/v5/authentication/password_based%3Abuilt_in_database/import_users'`;
                exec(importCommand, (importError, importStdout, importStderr) => {
                    if (importError) {
                        console.error(`Import exec error: ${importError}`);
                        return res.status(500).json({ error: 'Could not import user' });
                    }

                    console.log(`Import stdout: ${importStdout}`);
                    console.error(`Import stderr: ${importStderr}`);

                    // Create CSV content
                    const csvData = [
                        {
                            aesKey: aesKey.toString('hex'),
                            iv: iv.toString('hex')
                        }
                    ];
                    const json2csvParser = new Parser();
                    const csv = json2csvParser.parse(csvData);

                    // Set response headers to download the CSV file
                    res.header('Content-Type', 'text/csv');
                    res.header('Content-Disposition', `attachment; filename="${email}_keys.csv"`);
                    res.send(csv);
                });
            } catch (parseError) {
                console.error(`Parse error: ${parseError}`);
                res.status(500).json({ error: 'Could not parse token response' });
            }
        });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Could not register user' });
    }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
