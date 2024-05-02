
module.exports = {
    plugins: [
        require('@fullhuman/postcss-purgecss')({
            content:  [
                'src/all-layouts.html',
                '../multifactor/templates/**/*html',
            ],
            variables: true,
        }),
        require('postcss-variable-compress'),
    ],
}