const webpack = require('webpack');
const TerserPlugin = require('terser-webpack-plugin');

module.exports = (env, argv) => ({
    entry: [
        './golink/react/src/index.jsx'
    ],
    module: {
        rules: [
            {
                test: /\.(js|jsx)$/,
                exclude: /node_modules/,
                use: ['babel-loader']
            },
            {
                test: /\.css$/,
                loader: ['style-loader', 'css-loader']
            }
        ]
    },
    output: {
        path: __dirname + '/golink/static/js',
        filename: 'golink.js'
    },
    resolve: {
        extensions: ['.js', '.jsx'],
    },
    optimization: {
      minimize: (argv.mode === 'production') ? true : false,
      minimizer: [new TerserPlugin()],
    },
});
