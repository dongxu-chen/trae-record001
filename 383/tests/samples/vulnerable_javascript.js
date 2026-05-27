const express = require('express');
const mysql = require('mysql');
const fs = require('fs');
const { exec, execSync, execFile, spawn } = require('child_process');
const app = express();

const connection = mysql.createConnection({
  host: 'localhost',
  user: 'root',
  password: 'password',
  database: 'mydb'
});

app.get('/user', (req, res) => {
  const userId = req.query.id;
  const query = "SELECT * FROM users WHERE id = " + userId;
  connection.query(query, (err, results) => {
    res.json(results);
  });
});

app.get('/search', (req, res) => {
  const keyword = req.query.q;
  const query = `SELECT * FROM products WHERE name LIKE '%${keyword}%'`;
  connection.query(query, (err, results) => {
    res.json(results);
  });
});

app.get('/search_safe', (req, res) => {
  const keyword = req.query.q;
  connection.query(
    'SELECT * FROM products WHERE name LIKE ?',
    [`%${keyword}%`],
    (err, results) => {
      res.json(results);
    }
  );
});

app.get('/page', (req, res) => {
  const content = req.query.content;
  res.send(`<html><body>${content}</body></html>`);
});

app.get('/render', (req, res) => {
  const data = req.query.data;
  res.write(`<div>${data}</div>`);
});

app.get('/file', (req, res) => {
  const filename = req.query.name;
  const filePath = '/var/www/files/' + filename;
  fs.readFile(filePath, 'utf8', (err, data) => {
    res.send(data);
  });
});

app.get('/download', (req, res) => {
  const filename = req.query.file;
  res.sendFile('/var/www/files/' + filename);
});

app.get('/run', (req, res) => {
  const cmd = req.query.cmd;
  exec('ping -c 3 ' + cmd, (err, stdout, stderr) => {
    res.send(stdout);
  });
});

app.get('/process', (req, res) => {
  const input = req.query.input;
  try {
    const result = execSync('echo ' + input);
    res.send(result.toString());
  } catch (e) {
    res.status(500).send('Error');
  }
});

app.get('/run_safe', (req, res) => {
  const cmd = req.query.cmd;
  const allowed = ['ls', 'cat', 'grep'];
  if (!allowed.includes(cmd)) {
    return res.status(400).send('Invalid command');
  }
  execFile(cmd, ['-la'], (err, stdout) => {
    res.send(stdout);
  });
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});

module.exports = app;
