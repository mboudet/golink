import React, { Component, createContext } from 'react'
import { BrowserRouter as Router, Route, Switch, Redirect } from 'react-router-dom'
import axios from 'axios'

import About from './routes/about'
import Home from './routes/home'
import File from './routes/file'
import Files from './routes/files'
import Search from './routes/search'
import GolinkNavigation from './navigation'

import 'react-bootstrap-table-next/dist/react-bootstrap-table2.min.css'
import 'bootstrap/dist/css/bootstrap.min.css'

export default class Routes extends Component {

  constructor (props) {
    super(props)
    this.state = {
      config: {
        proxyPath: document.getElementById('proxy_path').getAttribute('proxy_path'),
        perPage: 10
      }
    }
    this.cancelRequest
  }

  render () {

    return (
      <Router basename={this.state.config.proxyPath}>
        <div>
          <GolinkNavigation config={this.state.config} />
          <Switch>
            <Route path="/" exact component={() => (<Home config={this.state.config} />)} />
            <Route path="/search" exact component={() => (<Search config={this.state.config} />)} />
            <Route path="/about" exact component={() => (<About config={this.state.config} />)} />
            <Route path="/files" exact component={() => (<Files config={this.state.config} />)} />
            <Route path="/files/:uri" exact component={() => (<File config={this.state.config} />)} />
          </Switch>
          <br />
          <br />
        </div>
      </Router>
    )
  }
}
