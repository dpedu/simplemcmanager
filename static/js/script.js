function confirmReturn(url, message) {
	if(confirm(message)) {
		window.location = url;
	} else {
		return false;
	}
}