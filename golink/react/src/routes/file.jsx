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
      download_url: base_url + 'api/view/' + this.props.match.params.uri
    }
    this.downloadFile = this.downloadFile.bind(this)
    this.pullFile = this.pullFile.bind(this)
    this.handleChangeEmail = this.handleChangeEmail.bind(this)
    this.cancelRequest
  }

  downloadFile(event){
    let uri = this.props.match.params.uri;
    let requestUrl = '/api/download/' + uri;
    axios.get(requestUrl, {baseURL: this.props.config.proxyPath, cancelToken: new axios.CancelToken((c) => { this.cancelRequest = c }) })
      .then((response) => {
        FileDownload(response.data, this.state.file.file_name)
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
    if (file.status == "unpublished"){
      status = <Badge color="warning">Unavailable</Badge>
    }
    if (file.status == "pulling"){
      status = <Badge color="secondary">Pulling</Badge>
    }
    if (file.status == "pullable"){
      status = <Badge color="primary">Pullable</Badge>
      action = <Button size="sm" color="primary" disabled={this.validateEmail()} onClick={this.pullFile}>Pull file</Button>
      form = <FormGroup>
                <Label for="email">Optional notification email</Label>
                <Input type="email" name="email" id="email" placeholder="Your email" value={this.state.email} onChange={this.handleChangeEmail} />
              </FormGroup>
    }
    if (file.status == "starting" || file.status == "hashing"){
      status = <Badge color="warning">Publishing</Badge>
    }

    if (file.siblings.length){
      let filesColumns = [{
          dataField: 'version',
          text: 'File version',
          sort: true,
          formatter: (cell, row) => {
            return <h5><Badge pill color="primary">v{row.version}</Badge></h5>
          }
        },{
          dataField: 'publishing_date',
          text: 'Publishing date',
          sort: true
        }, {
          dataField: 'status',
          text: 'Status',
          sort: true,
          formatter: (cell, row) => {
            let pill = ""
            if (row.status == "available"){
              pill = <Badge color="success">Available</Badge>
            }
            if (row.status == "unavailable" || file.status == "failed"){
              pill = <Badge color="danger">Unavailable</Badge>
            }
            if (row.status == "pulling"){
              pill = <Badge color="secondary">Pulling</Badge>
            }
            if (row.status == "pullable"){
              pill = <Badge color="started">Pullable</Badge>
            }
            if (row.status == "starting" || file.status == "hashing"){
              pill = <Badge color="warning">Publishing</Badge>
            }
            return <h5>{pill}</h5>
          }
        }, {
          dataField: 'uri',
          text: '',
          formatter: (cell, row) => {
             return <Link to={"/files/" + row.uri}><Button type="button" color="primary"><i className="fa fa-external-link-alt" aria-hidden="true"></i> Show</Button></Link>
          },
        }]
      let defaultSorted = [{
        dataField: 'version',
        order: 'desc'
      }]

      siblings = (
        <Card>
          <CardBody>
            <CardTitle tag="h2">Other versions of this file ({file.siblings.length})</CardTitle>
            <CardText tag="div" className="text-center">
              <br/>
              <BootstrapTable
              classes="gopublish-table"
              wrapperClasses="gopublish-table-wrapper"
              tabIndexCell
              bootstrap4
              keyField='uri'
              data={file.siblings}
              columns={filesColumns}
              defaultSorted={defaultSorted}
              pagination={paginationFactory()}
            />
            </CardText>
          </CardBody>
        </Card>
      )
    }


    return (
      <div className="container">
        <Card>
          <CardHeader tag="h4">{status} <Badge pill color="primary" className="float-right">v{file.version}</Badge></CardHeader>
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
        {siblings}
      </div>
    )
  }
}

File.propTypes = {
  config: PropTypes.object,
  match: PropTypes.object
}

export default withRouter(File)
