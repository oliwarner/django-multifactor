require('./multifactor.scss')

function display_message(level, msg) {
	document.getElementById('card').classList.add(`has-background-${level}`, 'has-text-white', 'has-text-centered')
	document.getElementById('content').innerHTML = msg
}
window.display_error = function(msg) { display_message('danger', msg) }
window.display_succcess = function(msg) { display_message('success', msg) }


document.body.addEventListener('click', function (ev) {
	console.log(ev.target.classList)
	if (ev.target.classList.contains('delete')) {
		let carryOn = confirm('Are you sure you want to delete this factor?')
		console.log(carryOn)
		console.log(carryOn)
		console.log(carryOn)
		console.log(carryOn)
		if (!carryOn)
			ev.preventDefault()
	}
    else if ('collapse' in ev.target.dataset) {
    	ev.preventDefault()
        let target = document.getElementById(ev.target.dataset.collapse)
        target.classList.toggle('open')
    }
}, false)


