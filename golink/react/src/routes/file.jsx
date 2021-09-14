import React, { Component } from 'react'
import axios from 'axios'
import { Badge, Button, Card, CardHeader, CardTitle, CardBody, CardText, Form, FormGroup, Input, Label } from 'reactstrap'
import BootstrapTable from 'react-bootstrap-table-next'
import paginationFactory from 'react-bootstrap-table2-paginator'
import FileDownload from 'js-file-download'
import update from 'react-addons-update'
import { withRouter } from "react-router-dom";
import PropTypes from 'prop-types'
import Utils from '../classes/utils'
import { Link, Redirect } from 'react-router-dom'

import Home from './home'

class File extends Component {
  constructor (props) {
    super(props)
    this.utils = new Utils()
    let base_url = this.props.config.proxyPath == "/" ? "/" : this.props.config.proxyPath + "/"
    this.state = {
      isLoading: true,
      file: {siblings: []},
      email: "",
      download_url: base_url + 'api/download/' + this.props.match.params.uri
    }    
    this.pullFile = this.pullFile.bind(this)
    this.handleChangeEmail = this.handleChangeEmail.bind(this)
    this.cancelRequest
  }

  pullFile(event){
    let uri = this.props.match.params.uri;
    let requestUrl = '/api/pull/' + uri;
    let data = {email: this.state.email}
    axios.post(requestUrl, {baseURL: this.props.config.proxyPath, cancelToken: new axios.CancelToken((c) => { this.cancelRequest = c }) })
      .then((response) => {
        this.setState({
          error: true,
          errorMessage: error.response.data.errorMessage,
          status: error.response.status,
        })
      })
      .catch(error => {
        console.log(error, error.response.data.errorMessage)
        this.setState({
          error: true,
          errorMessage: error.response.data.errorMessage,
          status: error.response.status,
        })
      })
  }

  handleChangeEmail (event) {
    this.setState({
      email: event.target.value
    })
  }

  validateEmail () {
    let email = this.state.email
    if (email == ""){
      return true
    } else {
      let re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
      return re.test(String(email).toLowerCase())
    }
  }

  componentDidMount () {
    this.loadFile()
  }

  componentDidUpdate(prevProps) {
    if (prevProps.match.params.uri !== this.props.match.params.uri) {
      this.loadFile()
    }
  }


  loadFile() {
    let uri = this.props.match.params.uri;
    let requestUrl = '/api/view/' + uri
    axios.get(requestUrl, { baseURL: this.props.config.proxyPath, cancelToken: new axios.CancelToken((c) => { this.cancelRequest = c }) })
      .then(response => {
        this.setState({
          isLoading: false,
          file: response.data.file,
        })
      })
      .catch(error => {
        console.log(error.response)
        this.setState({
            error: true,
            errorCode: error.response.status,
            errorMessage: error.response.statusText,
        })
      })
  }

  componentWillUnmount () {
    this.cancelRequest()
  }

  render () {
    if (this.state.error) {
        return (
            <div className="container">
            <h2>Error <i>{this.state.errorCode}</i> fetching file: <i>{this.state.errorMessage}</i></h2>
            </div>
        )
    }
    
    let uri = this.props.match.params.uri;
    let file = this.state.file
    let contact = ""
    let status = ""
    let form = ""
    let action = ""
    let siblings = ""

    if (file.contact){
      contact = <>Contact: {file.contact} </>
    } else {
      contact = <>Owner: {file.owner} </>
    }

    status = <p></p>
    if (file.status == "available"){
      status = <Badge color="success">Available</Badge>
      action = <Button as="a" size="sm" color="success" href={this.state.download_url} target="_blank">Download file</Button>
    }
    if (file.status == "unavailable" || file.status == "failed"){
      status = <Badge color="danger">Unavailable</Badge>
    }
    if (file.status == "pulling"){
      status = <Badge color="secondary">Pulling</Badge>
    }
    if (file.status == "pullable"){
      status = <Badge color="started">Pullable</Badge>
      action = <Button size="sm" color="started" disabled={this.validateEmail()} onClick={this.pullFile}>Pull file</Button>
      form = <FormGroup>
                <Label for="email">Optional notification email</Label>
                <Input type="email" name="email" id="email" placeholder="Your email" value={this.state.email} onChange={this.handleChangeEmail} />
              </FormGroup>
    }
    if (file.status == "starting" || file.status == "hashing"){
      status = <Badge color="warning">Publishing</Badge>
    }

    return (
      <div className="container">
        <Card>
          <CardHeader tag="h4">{status}</CardHeader>
          <CardBody>
            <CardTitle tag="h2">Information about file {file.file_name}</CardTitle>
            <CardText>    
                File size: {this.utils.humanFileSize(file.size, true)}
                <br />
                {contact}
                <br />
                Publishing date: {file.publishing_date}
                <br />
                MD5: {file.hash}
                <br />
                {form}
                <br />
                {action}
            </CardText>
          </CardBody>
        </Card>
      </div>
    )
  }
}

File.propTypes = {
  config: PropTypes.object,
  match: PropTypes.object
}

export default withRouter(File)

