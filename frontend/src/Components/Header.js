import React from 'react';
import logo from '../Assets/logo.png';
import { Link } from "react-router-dom";
import '../Styles/Header.css'
const Header = () => {
  return (
    <div className='header'>
      <div className='heading'>
       <img src={logo} alt='logo'/>
       <h1>Uhaki</h1>
      </div>
      <div className='links'>
        <Link>Legal Resources</Link>
      </div>
    </div>
  )
}

export default Header
