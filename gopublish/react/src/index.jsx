import React from 'react'
import ReactDOM from 'react-dom'
import packageJson from '../../../package.json';

import Routes from './routes'

class App extends React.Component {
  render () {

    return (
      <Routes />
    )
  }
}

ReactDOM.render(<App/>, document.getElementById('app'))
