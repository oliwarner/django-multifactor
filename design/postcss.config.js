const postCssPurge = require('@fullhuman/postcss-purgecss');

module.exports = {
    plugins: [
        postCssPurge({
            content:  [
                'src/all-layouts.html',
                '../multifactor/templates/**/*html',
            ]
        }),
    ],
}