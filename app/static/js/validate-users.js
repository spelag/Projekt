const checkIfUserExists = () => {
    const registrationForm = document.forms['signup-form']
    const emailForm = registrationForm['e-mail']
    const email = emailForm.value
    axios.post('/register-validation', {
        email: email
    })
    .then((response) => {
        if (response.data.user_exists == "true") {
            emailForm.setCustomValidity("An account using this e-mail already exists, please log in instead.")
            emailForm.reportValidity()
        }
    }, (error) => {
        console.log(error)
    })
}