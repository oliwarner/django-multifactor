const path = require('path');
const glob = require('glob')
const MiniCssExtractPlugin = require('mini-css-extract-plugin')
const PurgecssPlugin = require('purgecss-webpack-plugin')
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");

module.exports = {
  entry: './src/index.js',
  output: {
    path: path.resolve(__dirname, '../multifactor/static/multifactor'),  // in django static
    filename: 'js/multifactor.bundle.js'
  },
  devtool: 'source-map',
  module: {
    rules: [{
      test: /\.scss$/,
      use: [

          MiniCssExtractPlugin.loader,
          {
            loader: 'css-loader'
          },
          {
            loader: 'sass-loader',
            options: {
              sourceMap: true,
              sassOptions: {
                sourceMap: true,
                includePaths: [
                  require('path').resolve(__dirname, 'node_modules')
                ],
              },
            }
          }
        ]
    }]
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: 'css/multifactor-[name].bundle.css'
    }),
    new PurgecssPlugin({
      // hook into demo style page and the django template directory
      paths: [
        path.join(__dirname, 'src/all-layouts.html'),
        ...glob.sync(path.join(__dirname, '../multifactor/templates/**/*'),  { nodir: true }),
      ],
    }),
  ],

  optimization: {
    minimizer: [
      new CssMinimizerPlugin(),
    ],
  },
};