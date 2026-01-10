module.exports = {
    env: {
        browser: true,
        es2021: true,
    },
    parserOptions: {
        ecmaVersion: 'latest',
    },
    rules: {
        'no-undef': 'error',
        'no-unused-vars': 'warn',
        'no-unreachable': 'error',
        'no-constant-condition': 'warn',
    },
};
