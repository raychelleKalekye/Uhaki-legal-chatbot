import React from 'react';
import logo from '../Assets/logo.png';

import '../Styles/Header.css'
const Header = () => {
  return (
    <div className='header'>
      <div className='heading'>
       <img src={logo} alt='logo'/>
       <h1>Uhaki</h1>
      </div>
     
    </div>
  )
}

export default Header
