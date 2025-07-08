const profielImage = document.getElementById('profileImage')
const click = document.getElementById('click')
const prof = document.getElementById('profile')

profielImage.addEventListener('click', () => {
    if(value == null){
        click.classList.add('active');
        prof.classList.add('active');
        value = 'active'; 
    }
    else{
        click.classList.remove('active');
        prof.classList.remove('active');
        value = null; 
    }
});