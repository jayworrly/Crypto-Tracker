const concurrently = require('concurrently');
const path = require('path');

concurrently([
  {
    command: 'npm start',
    name: 'REACT',
    cwd: path.resolve(__dirname, 'frontend'),
    prefixColor: 'blue'
  },
  {
    command: 'python app.py',
    name: 'FLASK',
    cwd: path.resolve(__dirname, 'backend'),
    prefixColor: 'green'
  }
], {
  prefix: 'name',
  killOthers: ['failure', 'success'],
  restartTries: 3,
});
